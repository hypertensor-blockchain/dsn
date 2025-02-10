"""
Originally taken from: https://github.com/opentensor/bittensor/blob/master/bittensor/core/chain_data/utils.py
Licence: MIT
Author: Yuma Rao
"""

import ast
from enum import Enum
import json
import scalecodec
from dataclasses import dataclass
from scalecodec.base import RuntimeConfiguration, ScaleBytes
from typing import List, Dict, Optional, Any, Union
from scalecodec.type_registry import load_type_registry_preset
from scalecodec.utils.ss58 import ss58_encode
from hivemind import PeerID

U16_MAX = 65535
U64_MAX = 18446744073709551615

def U16_NORMALIZED_FLOAT(x: int) -> float:
  return float(x) / float(U16_MAX)

def U64_NORMALIZED_FLOAT(x: int) -> float:
  return float(x) / float(U64_MAX)

custom_rpc_type_registry = {
  "types": {
    "SubnetNode": {
      "type": "struct",
      "type_mapping": [
        ["account_id", "AccountId"],
        ["hotkey", "AccountId"],
        ["peer_id", "Vec<u8>"],
        ["initialized", "u64"],
        ["classification", "SubnetNodeClassification"],
        # ["delegate_reward_rate": "128"],
        ["a", "Vec<u8>"],
        ["b", "Vec<u8>"],
        ["c", "Vec<u8>"],
      ],
    },
    "SubnetNodeClassification": {
      "type": "struct",
      "type_mapping": [
        ["class", "SubnetNodeClass"],
        ["start_epoch", "u64"],
      ],
    },
    "SubnetNodeClass": {
      "type": "enum",
      "value_list": [
        "Registered", 
        "Idle", 
        "Included", 
        "Submittable", 
        "Accountant"
      ],
    },
    "RewardsData": {
      "type": "struct",
      "type_mapping": [
        ["peer_id", "Vec<u8>"],
        ["score", "u128"],
      ],
    },
    "SubnetNodeInfo": {
      "type": "struct",
      "type_mapping": [
        ["account_id", "AccountId"],
        ["hotkey", "AccountId"],
        ["peer_id", "Vec<u8>"],
      ],
    },
  }
}

class ChainDataType(Enum):
  """
  Enum for chain data types.
  """
  SubnetNode = 1
  RewardsData = 2
  SubnetNodeInfo = 3

def from_scale_encoding(
    input: Union[List[int], bytes, ScaleBytes],
    type_name: ChainDataType,
    is_vec: bool = False,
    is_option: bool = False,
) -> Optional[Dict]:
    """
    Returns the decoded data from the SCALE encoded input.

    Args:
      input (Union[List[int], bytes, ScaleBytes]): The SCALE encoded input.
      type_name (ChainDataType): The ChainDataType enum.
      is_vec (bool): Whether the input is a Vec.
      is_option (bool): Whether the input is an Option.

    Returns:
      Optional[Dict]: The decoded data
    """
    
    type_string = type_name.name
    if is_option:
      type_string = f"Option<{type_string}>"
    if is_vec:
      type_string = f"Vec<{type_string}>"

    return from_scale_encoding_using_type_string(input, type_string)

def from_scale_encoding_using_type_string(
  input: Union[List[int], bytes, ScaleBytes], type_string: str
) -> Optional[Dict]:
  """
  Returns the decoded data from the SCALE encoded input using the type string.

  Args:
    input (Union[List[int], bytes, ScaleBytes]): The SCALE encoded input.
    type_string (str): The type string.

  Returns:
    Optional[Dict]: The decoded data
  """
  if isinstance(input, ScaleBytes):
    as_scale_bytes = input
  else:
    if isinstance(input, list) and all([isinstance(i, int) for i in input]):
      vec_u8 = input
      as_bytes = bytes(vec_u8)
    elif isinstance(input, bytes):
      as_bytes = input
    else:
      raise TypeError("input must be a List[int], bytes, or ScaleBytes")

    as_scale_bytes = scalecodec.ScaleBytes(as_bytes)

  rpc_runtime_config = RuntimeConfiguration()
  rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
  rpc_runtime_config.update_type_registry(custom_rpc_type_registry)

  obj = rpc_runtime_config.create_scale_object(type_string, data=as_scale_bytes)

  return obj.decode()

# Dataclasses for chain data.
@dataclass
class AccountantDataParams:
  """
  Dataclass for accountant data
  """

  peer_id: PeerID
  span_start: int
  span_end: int
  accountant_tensor_sum: float
  tensor_sum: float
  valid: bool

  @classmethod
  def fix_decoded_values(cls, accountant_data_decoded: Any) -> "AccountantDataParams":
    """Fixes the values of the AccountantDataParams object."""

    accountant_data_decoded["peer_id"] = accountant_data_decoded["peer_id"]
    accountant_data_decoded["span_start"] = accountant_data_decoded["span_start"]
    accountant_data_decoded["span_end"] = accountant_data_decoded["span_end"]
    accountant_data_decoded["accountant_tensor_sum"] = accountant_data_decoded["accountant_tensor_sum"]
    accountant_data_decoded["tensor_sum"] = accountant_data_decoded["tensor_sum"]
    accountant_data_decoded["valid"] = accountant_data_decoded["valid"]

    return cls(**accountant_data_decoded)

  @classmethod
  def list_from_vec_u8(cls, vec_u8: List[int]) -> List["AccountantDataParams"]:
    """Returns a list of AccountantDataParams objects from a ``vec_u8``."""
    """The data is arbitrary so we don't count on a struct"""

    decoded_list: List[AccountantDataParams] = []

    # Convert arbitrary data to str
    list_of_ord_values = ''.join(chr(i) for i in vec_u8)

    # Replace ' to " for json
    list_of_ord_values = list_of_ord_values.replace("\'", "\"")

    json_obj = json.loads(list_of_ord_values)

    for x in json_obj:
      accountant_data_params = AccountantDataParams(*x)
      decoded_list.append(accountant_data_params)

    return decoded_list

@dataclass
class RewardsData:
  """
  Dataclass for model peer metadata.
  """

  peer_id: str
  score: int

  @classmethod
  def fix_decoded_values(cls, rewards_data_decoded: Any) -> "RewardsData":
    """Fixes the values of the RewardsData object."""
    rewards_data_decoded["peer_id"] = rewards_data_decoded["peer_id"]
    rewards_data_decoded["score"] = rewards_data_decoded["score"]

    return cls(**rewards_data_decoded)

  @classmethod
  def from_vec_u8(cls, vec_u8: List[int]) -> "RewardsData":
    """Returns a RewardsData object from a ``vec_u8``."""

    if len(vec_u8) == 0:
      return RewardsData._null_subnet_node_data()

    decoded = from_scale_encoding(vec_u8, ChainDataType.RewardsData)

    if decoded is None:
      return RewardsData._null_subnet_node_data()

    decoded = RewardsData.fix_decoded_values(decoded)

    return decoded

  @classmethod
  def list_from_vec_u8(cls, vec_u8: List[int]) -> List["RewardsData"]:
    """Returns a list of RewardsData objects from a ``vec_u8``."""

    decoded_list = from_scale_encoding(
      vec_u8, ChainDataType.RewardsData, is_vec=True
    )
    if decoded_list is None:
      return []

    decoded_list = [
      RewardsData.fix_decoded_values(decoded) for decoded in decoded_list
    ]
    return decoded_list

  @classmethod
  def list_from_scale_info(cls, scale_info: Any) -> List["RewardsData"]:
    """Returns a list of RewardsData objects from a ``decoded_list``."""

    encoded_list = []
    for code in map(ord, str(scale_info)):
      encoded_list.append(code)


    decoded = ''.join(map(chr, encoded_list))

    json_data = ast.literal_eval(json.dumps(decoded))

    decoded_list = []
    for item in scale_info:
      decoded_list.append(
        RewardsData(
          peer_id=str(item["peer_id"]),
          score=int(str(item["score"])),
        )
      )

    return decoded_list

  @staticmethod
  def _rewards_data_to_namespace(rewards_data) -> "RewardsData":
    """
    Converts a RewardsData object to a namespace.

    Args:
      rewards_data (RewardsData): The RewardsData object.

    Returns:
      RewardsData: The RewardsData object.
    """
    data = RewardsData(**rewards_data)

    return data

@dataclass
class SubnetNodeInfo:
  """
  Dataclass for model peer metadata.
  """

  account_id: str
  hotkey: str
  peer_id: str

  @classmethod
  def fix_decoded_values(cls, data_decoded: Any) -> "SubnetNodeInfo":
    """Fixes the values of the RewardsData object."""
    data_decoded["account_id"] = ss58_encode(
      data_decoded["account_id"], 42
    )
    data_decoded["hotkey"] = data_decoded["hotkey"]
    data_decoded["peer_id"] = data_decoded["peer_id"]

    return cls(**data_decoded)

  @classmethod
  def from_vec_u8(cls, vec_u8: List[int]) -> "SubnetNodeInfo":
    """Returns a SubnetNodeInfo object from a ``vec_u8``."""

    if len(vec_u8) == 0:
      return SubnetNodeInfo._null_subnet_node_data()

    decoded = from_scale_encoding(vec_u8, ChainDataType.SubnetNodeInfo)

    if decoded is None:
      return SubnetNodeInfo._null_subnet_node_data()

    decoded = SubnetNodeInfo.fix_decoded_values(decoded)

    return decoded

  @classmethod
  def list_from_vec_u8(cls, vec_u8: List[int]) -> List["SubnetNodeInfo"]:
    """Returns a list of SubnetNodeInfo objects from a ``vec_u8``."""

    decoded_list = from_scale_encoding(
      vec_u8, ChainDataType.SubnetNodeInfo, is_vec=True
    )
    if decoded_list is None:
      return []

    decoded_list = [
      SubnetNodeInfo.fix_decoded_values(decoded) for decoded in decoded_list
    ]
    return decoded_list

  @staticmethod
  def _subnet_node_info_to_namespace(data) -> "SubnetNodeInfo":
    """
    Converts a SubnetNodeInfo object to a namespace.

    Args:
      rewards_data (SubnetNodeInfo): The SubnetNodeInfo object.

    Returns:
      SubnetNodeInfo: The SubnetNodeInfo object.
    """
    data = SubnetNodeInfo(**data)

    return data

@dataclass
class SubnetNode:
  """
  Dataclass for model peer metadata.
  """

  account_id: str
  hotkey: str
  peer_id: str
  initialized: int
  classification: str
  # delegate_reward_rate: int
  a: str
  b: str
  c: str

  @classmethod
  def fix_decoded_values(cls, data_decoded: Any) -> "SubnetNode":
    """Fixes the values of the RewardsData object."""
    data_decoded["account_id"] = ss58_encode(
      data_decoded["account_id"], 42
    )
    data_decoded["hotkey"] = data_decoded["hotkey"]
    data_decoded["peer_id"] = data_decoded["peer_id"]
    data_decoded["initialized"] = data_decoded["initialized"]
    data_decoded["classification"] = data_decoded["classification"]
    # data_decoded["delegate_reward_rate"] = data_decoded["delegate_reward_rate"]
    data_decoded["a"] = data_decoded["a"]
    data_decoded["b"] = data_decoded["b"]
    data_decoded["c"] = data_decoded["c"]

    return cls(**data_decoded)

  @classmethod
  def list_from_vec_u8(cls, vec_u8: List[int]) -> List["SubnetNode"]:
    """Returns a list of SubnetNode objects from a ``vec_u8``."""

    decoded_list = from_scale_encoding(
      vec_u8, ChainDataType.SubnetNode, is_vec=True
    )
    if decoded_list is None:
      return []

    decoded_list = [
      SubnetNode.fix_decoded_values(decoded) for decoded in decoded_list
    ]
    return decoded_list

  @staticmethod
  def _subnet_node_info_to_namespace(data) -> "SubnetNode":
    """
    Converts a SubnetNode object to a namespace.

    Args:
      rewards_data (SubnetNode): The SubnetNode object.

    Returns:
      SubnetNode: The SubnetNode object.
    """
    data = SubnetNodeInfo(**data)

    return data