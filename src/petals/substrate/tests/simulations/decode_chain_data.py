
from enum import Enum
import base58
from scalecodec import ScaleBytes, Vec
from scalecodec.base import ScaleDecoder
from substrateinterface.utils.ss58 import ss58_encode
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from scalecodec.base import RuntimeConfiguration, ScaleBytes
from scalecodec.type_registry import load_type_registry_preset

from petals.substrate.chain_data import SubnetNode, SubnetNodeInfo, from_scale_encoding

"""
This test requires a build with a subnet already initialized into the network pallet
"""
# python src/petals/substrate/tests/simulations/decode_chain_data.py


# Manually decode a Vec<AccountId>
class AccountId(ScaleDecoder):
    def process(self):
        # AccountId is a fixed 32-byte array
        public_key = self.get_next_bytes(32)
        return public_key

class AccountIdVec(Vec):
    element_type = AccountId

vec_u8 = [20, 42, 251, 169, 39, 142, 48, 204, 246, 166, 206, 179, 168, 182, 227, 54, 183, 0, 104, 240, 69, 198, 102, 242, 231, 244, 249, 204, 95, 71, 219, 137, 114, 42, 251, 169, 39, 142, 48, 204, 246, 166, 206, 179, 168, 182, 227, 54, 183, 0, 104, 240, 69, 198, 102, 242, 231, 244, 249, 204, 95, 71, 219, 137, 114, 184, 81, 109, 101, 100, 84, 97, 90, 88, 109, 85, 76, 113, 119, 115, 112, 74, 88, 122, 52, 52, 83, 115, 80, 90, 121, 84, 78, 75, 120, 104, 110, 110, 70, 118, 89, 82, 97, 106, 102, 72, 55, 77, 71, 104, 67, 89, 5, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 70, 241, 54, 181, 100, 225, 250, 213, 80, 49, 64, 77, 216, 78, 92, 211, 250, 118, 191, 231, 204, 117, 153, 179, 157, 56, 253, 6, 102, 59, 188, 10, 70, 241, 54, 181, 100, 225, 250, 213, 80, 49, 64, 77, 216, 78, 92, 211, 250, 118, 191, 231, 204, 117, 153, 179, 157, 56, 253, 6, 102, 59, 188, 10, 208, 49, 50, 68, 51, 75, 111, 111, 87, 66, 120, 77, 76, 106, 101, 55, 121, 69, 120, 69, 66, 104, 90, 81, 113, 98, 117, 86, 76, 49, 103, 105, 75, 80, 112, 78, 56, 68, 105, 101, 89, 107, 76, 51, 87, 122, 55, 115, 84, 107, 117, 55, 84, 7, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 72, 215, 233, 49, 48, 122, 251, 75, 104, 216, 213, 101, 212, 198, 110, 0, 216, 86, 198, 214, 95, 95, 237, 107, 184, 45, 207, 182, 14, 147, 108, 103, 72, 215, 233, 49, 48, 122, 251, 75, 104, 216, 213, 101, 212, 198, 110, 0, 216, 86, 198, 214, 95, 95, 237, 107, 184, 45, 207, 182, 14, 147, 108, 103, 208, 49, 50, 68, 51, 75, 111, 111, 87, 74, 65, 65, 113, 98, 66, 87, 51, 89, 88, 74, 69, 52, 50, 84, 65, 71, 103, 88, 84, 82, 86, 120, 90, 119, 109, 87, 117, 113, 89, 57, 121, 66, 110, 101, 76, 102, 115, 68, 70, 105, 65, 56, 98, 9, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 132, 97, 127, 87, 83, 114, 237, 181, 163, 109, 133, 192, 76, 223, 46, 70, 153, 249, 111, 227, 62, 181, 249, 74, 40, 192, 65, 184, 142, 57, 141, 12, 132, 97, 127, 87, 83, 114, 237, 181, 163, 109, 133, 192, 76, 223, 46, 70, 153, 249, 111, 227, 62, 181, 249, 74, 40, 192, 65, 184, 142, 57, 141, 12, 208, 49, 50, 68, 51, 75, 111, 111, 87, 69, 68, 89, 109, 112, 81, 86, 87, 54, 105, 120, 68, 55, 77, 105, 106, 99, 105, 90, 99, 90, 77, 117, 80, 116, 100, 114, 118, 78, 98, 101, 67, 52, 74, 114, 49, 99, 120, 86, 49, 104, 74, 90, 101, 8, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 182, 6, 252, 115, 245, 127, 3, 205, 180, 201, 50, 212, 117, 171, 66, 96, 67, 228, 41, 206, 204, 47, 255, 240, 210, 103, 43, 13, 248, 57, 140, 72, 182, 6, 252, 115, 245, 127, 3, 205, 180, 201, 50, 212, 117, 171, 66, 96, 67, 228, 41, 206, 204, 47, 255, 240, 210, 103, 43, 13, 248, 57, 140, 72, 184, 81, 109, 81, 71, 84, 113, 109, 77, 55, 78, 75, 106, 86, 54, 103, 103, 85, 49, 90, 67, 97, 112, 56, 122, 87, 105, 121, 75, 82, 56, 57, 82, 86, 105, 68, 88, 105, 113, 101, 104, 83, 105, 67, 112, 89, 53, 6, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
subnet_node_info = [20, 42, 251, 169, 39, 142, 48, 204, 246, 166, 206, 179, 168, 182, 227, 54, 183, 0, 104, 240, 69, 198, 102, 242, 231, 244, 249, 204, 95, 71, 219, 137, 114, 42, 251, 169, 39, 142, 48, 204, 246, 166, 206, 179, 168, 182, 227, 54, 183, 0, 104, 240, 69, 198, 102, 242, 231, 244, 249, 204, 95, 71, 219, 137, 114, 184, 81, 109, 101, 100, 84, 97, 90, 88, 109, 85, 76, 113, 119, 115, 112, 74, 88, 122, 52, 52, 83, 115, 80, 90, 121, 84, 78, 75, 120, 104, 110, 110, 70, 118, 89, 82, 97, 106, 102, 72, 55, 77, 71, 104, 67, 89, 70, 241, 54, 181, 100, 225, 250, 213, 80, 49, 64, 77, 216, 78, 92, 211, 250, 118, 191, 231, 204, 117, 153, 179, 157, 56, 253, 6, 102, 59, 188, 10, 70, 241, 54, 181, 100, 225, 250, 213, 80, 49, 64, 77, 216, 78, 92, 211, 250, 118, 191, 231, 204, 117, 153, 179, 157, 56, 253, 6, 102, 59, 188, 10, 208, 49, 50, 68, 51, 75, 111, 111, 87, 66, 120, 77, 76, 106, 101, 55, 121, 69, 120, 69, 66, 104, 90, 81, 113, 98, 117, 86, 76, 49, 103, 105, 75, 80, 112, 78, 56, 68, 105, 101, 89, 107, 76, 51, 87, 122, 55, 115, 84, 107, 117, 55, 84, 72, 215, 233, 49, 48, 122, 251, 75, 104, 216, 213, 101, 212, 198, 110, 0, 216, 86, 198, 214, 95, 95, 237, 107, 184, 45, 207, 182, 14, 147, 108, 103, 72, 215, 233, 49, 48, 122, 251, 75, 104, 216, 213, 101, 212, 198, 110, 0, 216, 86, 198, 214, 95, 95, 237, 107, 184, 45, 207, 182, 14, 147, 108, 103, 208, 49, 50, 68, 51, 75, 111, 111, 87, 74, 65, 65, 113, 98, 66, 87, 51, 89, 88, 74, 69, 52, 50, 84, 65, 71, 103, 88, 84, 82, 86, 120, 90, 119, 109, 87, 117, 113, 89, 57, 121, 66, 110, 101, 76, 102, 115, 68, 70, 105, 65, 56, 98, 132, 97, 127, 87, 83, 114, 237, 181, 163, 109, 133, 192, 76, 223, 46, 70, 153, 249, 111, 227, 62, 181, 249, 74, 40, 192, 65, 184, 142, 57, 141, 12, 132, 97, 127, 87, 83, 114, 237, 181, 163, 109, 133, 192, 76, 223, 46, 70, 153, 249, 111, 227, 62, 181, 249, 74, 40, 192, 65, 184, 142, 57, 141, 12, 208, 49, 50, 68, 51, 75, 111, 111, 87, 69, 68, 89, 109, 112, 81, 86, 87, 54, 105, 120, 68, 55, 77, 105, 106, 99, 105, 90, 99, 90, 77, 117, 80, 116, 100, 114, 118, 78, 98, 101, 67, 52, 74, 114, 49, 99, 120, 86, 49, 104, 74, 90, 101, 182, 6, 252, 115, 245, 127, 3, 205, 180, 201, 50, 212, 117, 171, 66, 96, 67, 228, 41, 206, 204, 47, 255, 240, 210, 103, 43, 13, 248, 57, 140, 72, 182, 6, 252, 115, 245, 127, 3, 205, 180, 201, 50, 212, 117, 171, 66, 96, 67, 228, 41, 206, 204, 47, 255, 240, 210, 103, 43, 13, 248, 57, 140, 72, 184, 81, 109, 81, 71, 84, 113, 109, 77, 55, 78, 75, 106, 86, 54, 103, 103, 85, 49, 90, 67, 97, 112, 56, 122, 87, 105, 121, 75, 82, 56, 57, 82, 86, 105, 68, 88, 105, 113, 101, 104, 83, 105, 67, 112, 89, 53]

# account_id: 5D34dL5prEUaGNQtPPZ3yN5Y6BnkfXunKXXz6fo7ZJbLwRRH
# account_id: 5GBNeWRhZc2jXu7D55rBimKYDk8PGk8itRYFTPfC8RJLKG5o
# account_id: 5Dfis6XL8J2P6JHUnUtArnFWndn62SydeP8ee8sG2ky9nfm9
# account_id: 5F4H97f7nQovyrbiq4ZetaaviNwThSVcFobcA5aGab6167dK
# account_id: 5DiDShBWa1fQx6gLzpf3SFBhMinCoyvHM1BWjPNsmXS8hkrW

class ChainDataType(Enum):
  """
  Enum for chain data types.
  """
  SubnetNode = 1
  RewardsData = 2

custom_rpc_type_registry = {
  "types": {
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

# custom_rpc_type_registry = {
#   "types": {
#     "SubnetNode": {
#       "type": "struct",
#       "type_mapping": [
#         ["account_id", "AccountId"],
#         ["hotkey", "AccountId"],
#         ["peer_id", "Vec<u8>"],
#         ["initialized", "u64"],
#         ["classification", "SubnetNodeClassification"],
#         ["a", "Vec<u8>"],
#         ["b", "Vec<u8>"],
#         ["c", "Vec<u8>"],
#       ],
#     },
#     "SubnetNodeInfo": {
#       "type": "struct",
#       "type_mapping": [
#         ["account_id", "AccountId"],
#         ["hotkey", "AccountId"],
#         ["peer_id", "Vec<u8>"],
#       ],
#     },
#     "SubnetNodeClassification": {
#       "type": "struct",
#       "type_mapping": [
#         ["class", "SubnetNodeClass"],
#         ["start_epoch", "u64"],
#       ],
#     },
#     "SubnetNodeClass": {
#       "type": "enum",
#       "value_list": [
#         "Registered", 
#         "Idle", 
#         "Included", 
#         "Submittable", 
#         "Accountant"
#       ],
#     },
#   }
# }
def decode_account_ids():
  info_data = SubnetNodeInfo.list_from_vec_u8(subnet_node_info)
  print("decode_account_ids info_data", info_data)



  data = SubnetNode.list_from_vec_u8(vec_u8)
  print("decode_account_ids data", data)

  # rpc_runtime_config = RuntimeConfiguration()
  # rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
  # rpc_runtime_config.update_type_registry(custom_rpc_type_registry)
  # # print("decode_account_ids rpc_runtime_config", rpc_runtime_config.type_registry)

  # obj = rpc_runtime_config.create_scale_object("Vec<SubnetNode>", data=ScaleBytes(bytes(vec_u8)))

  # print("decode_account_ids obj", obj)

  # rpc_runtime_config = RuntimeConfiguration()
  # rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
  # rpc_runtime_config.update_type_registry(custom_rpc_type_registry)

  # scale_obj = rpc_runtime_config.create_scale_object("Vec<SubnetNode>")

  # type_info = scale_obj.generate_type_decomposition()
  # print("decode_account_ids type_info", type_info)

  # obj = rpc_runtime_config.create_scale_object("Vec<SubnetNode>", data=ScaleBytes(bytes(vec_u8)))
  # print("decode_account_ids obj", obj)

  # rpc_runtime_config = RuntimeConfiguration()
  # rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
  # rpc_runtime_config.update_type_registry(custom_rpc_type_registry)

  # scale_obj = rpc_runtime_config.create_scale_object("Vec<SubnetNodeInfo>")

  # type_info = scale_obj.generate_type_decomposition()
  # print("decode_account_ids type_info", type_info)

  # obj = rpc_runtime_config.create_scale_object("Vec<SubnetNodeInfo>", data=ScaleBytes(bytes(subnet_node_info)))
  # print("decode_account_ids obj", obj)

  # # Convert the array to bytes
  # account_ids_bytes = bytes(vec_u8)

  # # Process the Vec<AccountId>
  # decoded_account_ids = []
  # account_id_length = 32  # sr25519 public keys are 32 bytes long

  # # Extract chunks of 32 bytes
  # for i in range(0, len(account_ids_bytes), account_id_length):
  #     account_id = account_ids_bytes[i:i + account_id_length]
  #     if len(account_id) == account_id_length:
  #         try:
  #             # Validate the key using sr25519
  #             VerifyKey(account_id)  # This ensures the key is valid
  #             # Convert to SS58 address (base58-encoded format with prefix 0)
  #             prefix = b'\x00'  # Prefix for SS58 (default Substrate networks)
  #             checksum = base58.b58encode_check(prefix + account_id).decode()
  #             decoded_account_ids.append(checksum)
  #         except BadSignatureError:
  #             print(f"Invalid sr25519 key detected: {account_id.hex()}")

  # # Output the results
  # for i, account_id in enumerate(decoded_account_ids):
  #   print(f"Account ID {i + 1} (SS58 format): {account_id}")

  # decoded_list = from_scale_encoding(
  #   vec_u8, ChainDataType.SubnetNode, is_vec=True
  # )
  # print("SubnetNode list_from_vec_u8 decoded_list", decoded_list)

  # if decoded_list is None:
  #   return []

  # decoded_list = [
  #   SubnetNode.fix_decoded_values(decoded) for decoded in decoded_list
  # ]
  # print("SubnetNode list_from_vec_u8 decoded_list", decoded_list)


if __name__ == "__main__":
  decode_account_ids()