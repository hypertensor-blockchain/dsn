"""
A quick low resources way to benchmark a peers inference speed
Also works to loosely validate the peer is hosting the transformer blocks they say they are
"""
import asyncio
from functools import partial
import pprint
import time
from typing import Any, Dict, List, Optional
import hivemind
from hivemind import PeerID, DHT
from hivemind.utils import DHTExpiration, get_dht_time
from hivemind.dht import DHTNode
from hivemind.utils.auth import AuthorizerBase
from hivemind.dht.routing import DHTKey
from hivemind.dht.crypto import Ed25519SignatureValidator, RecordValidatorBase
import numpy as np
import torch
import math

from subnet.client.remote_sequential import RemoteSequential
from subnet.constants import DTYPE_MAP, PUBLIC_INITIAL_PEERS
from subnet.health.state_updater import IncentivesProtocol, ScoringProtocol
from subnet.server.throughput import synchronize
from subnet.substrate.chain_functions import get_subnet_id_by_path
from subnet.substrate.config import SubstrateConfigCustom
from subnet.utils.auto_config import AutoDistributedConfig

from hivemind.proto import crypto_pb2
from hivemind.utils.crypto import Ed25519PrivateKey, Ed25519PublicKey
from hivemind.utils.auth import POSAuthorizerLive, POSAuthorizer
from cryptography.hazmat.primitives.asymmetric import ed25519
import gc

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

RPC = os.getenv('LOCAL_RPC')
PHRASE = os.getenv('PHRASE')
# MODEL_NAME = "bigscience/bloom-560m-petals"
MODEL_NAME = "Orenguteng/Llama-3.1-8B-Lexi-Uncensored-V2"

# python ./src/subnet/validator/measure_compute.py

async def compute_peers_rps(
  model_name: str, 
  initial_peers: List[str], 
  subnet_id: int, 
  identity_path: str,
  rpc_url: str,
  model_report,
  authorizer: Optional[AuthorizerBase] = None,
  record_validator: Optional[RecordValidatorBase] = None,
  max_length: Optional[int] = 100,
  torch_dtype: Optional[str] = "float32",
  **kwargs,
):
  config = AutoDistributedConfig.from_pretrained(
    model_name,
    subnet_id=subnet_id,
    identity_path=identity_path,
    rpc=rpc_url,
  )

  dht = DHT(
    initial_peers=initial_peers, 
    client_mode=True, 
    start=True,
    record_validators=[record_validator],
    **dict(kwargs, authorizer=authorizer)
  )

  num_blocks = model_report['model_reports'][0]['num_blocks']
  times = []

  if torch.cuda.is_available():
      device = "cuda"
  elif torch.backends.mps.is_available():
      device = "mps"
  else:
      device = "cpu"
  device = torch.device(device)

  for _ in range(0, 1):
    for server in model_report['model_reports'][0]["server_rows"]:
      start_block = server["span"].start
      end_block = server["span"].end
      peer_id = server["peer_id"]
      config.allowed_servers = [peer_id]

      blocks = RemoteSequential(
        config, 
        dht=dht, 
        start_block=start_block,
        end_block=end_block,
        subnet_id=subnet_id,
        identity_path=identity_path,
        rpc=rpc_url
      )

      blocks_served_ratio = (end_block - start_block) / num_blocks
      n_steps = 24
      n_steps = max(n_steps, int(n_steps / blocks_served_ratio))
      scaling_factor1 = math.pow(blocks_served_ratio, 1-math.sqrt(blocks_served_ratio))
      scaling_factorq = math.sqrt(blocks_served_ratio)
      scaling_factor = (blocks_served_ratio / scaling_factor1)

      max_length = max(n_steps, max_length)  

      warmup_steps = 5
      n_tokens = 1
      rps_data = await measure_inference_steps(
        blocks, 
        device,
        peer_id,
        start_block,
        end_block,
        blocks_served_ratio,
        scaling_factor,
        max_length,
        n_steps,
        warmup_steps,
        n_tokens,
        config
      )

      times.append(rps_data)

      gc.collect()
      time.sleep(6)

  pprint.pprint(times)

  # key = b"key"
  # subkey = b"protected_subkey" + record_validator.local_public_key

  # expiration_time = get_dht_time()+10
  # dht.run_coroutine(
  #   partial(_store_rps, key=key, subkey=subkey, value="times", expiration_time=expiration_time),
  #   return_future=False,
  # )

  # rps_get = dht.run_coroutine(
  #   partial(
  #     _get_rps,
  #     key=key,
  #     expiration_time=math.inf,
  #     latest=True,
  #   ),
  #   return_future=False,
  # )

  # for v in rps_get[key]:
  #   try:
  #     if isinstance(v, dict):
  #       print("rps_get k", v.keys())
  #       print("rps_get v", v.values())
  #       keys = list(v.keys())
  #       for key in keys:
  #         peer_id = extract_peer_id(record_validator, key)
  #         print("rps_get peer_id", peer_id)
  #   except Exception as e:
  #     print(e)


async def _store_rps(
  dht: DHT,
  node: DHTNode,
  key: Any,
  subkey: Any,
  value: Any,
  expiration_time: DHTExpiration,
) -> Dict[DHTKey, bool]:
  return await node.store(
    key=key,
    subkey=subkey,
    value=value,
    expiration_time=expiration_time,
    num_workers=32,
  )
  # store_ok = await node.store(
  #   key=key,
  #   subkey=subkey,
  #   value=value,
  #   expiration_time=expiration_time,
  #   num_workers=32,
  # )
  # print("store_ok", store_ok)
  # return store_ok


async def _get_rps(
  dht: DHT,
  node: DHTNode,
  key: Any,
  expiration_time: Optional[DHTExpiration],
  latest: bool,
) -> Any:
  found = await node.get_many([key], expiration_time)
  print("found", found)
  return found

async def measure_inference_steps(
  blocks: RemoteSequential, 
  device: torch.device,
  peer_id: PeerID,
  start_block: int,
  end_block: int,
  blocks_served_ratio: float,
  scaling_factor: float,
  max_length: int,
  n_steps: int,
  warmup_steps: int,
  n_tokens: int,
  config
):
  timed_result = None
  time_steps = []
  device = torch.device(device)
  with torch.inference_mode():
    synchronize(device)
    torch.manual_seed(42)  
    try:
      with blocks.inference_session(max_length=max_length) as sess:
        success = True
        for _ in range(0, n_steps):
          try:
            time, outputs = sess.timed_step(torch.empty(1, n_tokens, config.hidden_size), max_retries=0)
            if _ >= warmup_steps:
              time_steps.append(time)
          except hivemind.p2p.p2p_daemon_bindings.utils.P2PHandlerError as e:
            print("1", e)
            success = False
            break
          except Exception as e:
            print("2", e)
            success = False
            break

        if success:
          elapsed = sum(time_steps)
          device_rps_def = ((n_steps - warmup_steps) * n_tokens / elapsed)
          if blocks_served_ratio != 1.0:
            device_rps = ((n_steps - warmup_steps) * n_tokens) / elapsed * scaling_factor
          else:
            device_rps = (n_steps - warmup_steps) * n_tokens / elapsed
          timed_result = {
            'peer_id': peer_id.to_base58(),
            'start': start_block,
            'end':end_block,
            'elapsed': elapsed,
            'device_rps': device_rps,
            'device_rps_def': device_rps_def,
            'blocks_served_ratio': blocks_served_ratio,
            'steps': n_steps,
          }

    except Exception as e:
      print("Child 1 Exception", e)

  synchronize(device)
  return timed_result

async def measure_inference(
  blocks: RemoteSequential, 
  device: torch.device,
  peer_id: PeerID,
  start_block: int,
  end_block: int,
  blocks_served_ratio: float,
  scaling_factor: float,
  max_length: int,
  n_steps: int,
  warmup_steps: int,
  n_tokens: int,
  config
):
  timed_result = None
  time_steps = []
  device = torch.device(device)
  with torch.inference_mode():
    synchronize(device)
    torch.manual_seed(42)  
    try:
      with blocks.inference_session(max_length=max_length) as sess:
        success = True
        for _ in range(0, n_steps):
          try:
            if _ == warmup_steps:
              start_time = time.perf_counter()
            sess.step(torch.empty(1, n_tokens, config.hidden_size), max_retries=0)
          except hivemind.p2p.p2p_daemon_bindings.utils.P2PHandlerError as e:
            print("1", e)
            success = False
            break
          except Exception as e:
            print("2", e)
            success = False
            break

        elapsed = time.perf_counter() - start_time
        if success:
          device_rps_def = ((n_steps - warmup_steps) * n_tokens / elapsed)
          if blocks_served_ratio != 1.0:
            device_rps = ((n_steps - warmup_steps) * n_tokens) / elapsed * scaling_factor
          else:
            device_rps = (n_steps - warmup_steps) * n_tokens / elapsed
          timed_result = {
            'peer_id': peer_id.to_base58(),
            'start': start_block,
            'end':end_block,
            'elapsed': elapsed,
            'device_rps': device_rps,
            'device_rps_def': device_rps_def,
            'blocks_served_ratio': blocks_served_ratio,
            'steps': n_steps,
          }

    except Exception as e:
      print("Child 1 Exception", e)

  synchronize(device)
  return timed_result

def extract_peer_id(record_validator: RecordValidatorBase, key)-> Optional[PeerID]:
  public_keys = record_validator._PUBLIC_KEY_RE.findall(key)
  pubkey = Ed25519PublicKey.from_bytes(public_keys[0])
  peer_id = get_peer_id(pubkey)
  return peer_id

def get_peer_id(public_key: Ed25519PublicKey) -> Optional[PeerID]:
  try:
    encoded_public_key = crypto_pb2.PublicKey(
      key_type=crypto_pb2.Ed25519,
      data=public_key.to_raw_bytes(),
    ).SerializeToString()
    encoded_public_key = b"\x00$" + encoded_public_key
    peer_id = PeerID(encoded_public_key)
    return peer_id
  except:
    return None

if __name__ == "__main__":
  model_stripped = MODEL_NAME.rstrip("-petals")
  print("model_stripped", model_stripped)

  with open(f"private_key.key", "rb") as f:
    data = f.read()
    key_data = crypto_pb2.PrivateKey.FromString(data).data
    # private key stores with public because libp2p requires it as the ed25519 format
    raw_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])
    private_key = Ed25519PrivateKey(private_key=raw_private_key)
    public_key = private_key.get_public_key()

  """validator"""
  # substrate = SubstrateConfigCustom(PHRASE, RPC)
  # subnet_id = get_subnet_id_by_path(
  #   substrate.interface, 
  #   model_stripped
  # )
  # subnet_id = int(str(subnet_id))
  # print("subnet_id", subnet_id)
  # authorizer = POSAuthorizerLive(private_key, subnet_id, substrate.interface)

  # authorizer = POSAuthorizer(private_key)
  # incentives_protocol = IncentivesProtocol(authorizer, "private_key.key")
  # peers_data = incentives_protocol.run()
  # print("peers_data", peers_data)
  # model_state = "broken"
  # total_blockchain_model_peers_blocks = 0
  # model_num_blocks = 0
  # """Initial storage for blockchain peers"""
  # initial_blockchain_peers = []
  # blockchain_peers = []

  # for key, value in peers_data["model_report"].items():
  #   """State"""
  #   if key == "state":
  #     model_state = value
  #     if model_state == "broken":
  #       break

  #   """Number Of Blocks"""
  #   if key == "model_num_blocks":
  #     model_num_blocks = value

  #   """Model Peers"""
  #   if key == "server_rows":
  #     for server in value:
  #       peer_id = server['peer_id']
  #       print(peer_id)


    # for x in data:
    #   print("x", x)
      # print("value", value)

    # if key == "model_reports":
    #   for data in value:
    #     for model_key, model_value in data.items():
    #       """Model State"""
    #       if model_key == "state":
    #         model_state = model_value
    #         if model_state == "broken":
    #           break

    #       """Model Number Of Blocks"""
    #       if model_key == "model_num_blocks":
    #         model_num_blocks = model_value

    #       """Model Peers"""
    #       if model_key == "server_rows":
    #         for server in model_value:
    #           peer_id = server['peer_id']

    #           """Match Hosting Peers -> Blockchain Model Peers"""
    #           if blockchain_peer_id == peer_id:
                
    #             span_length = server['span'].length
    #             using_relay = server['using_relay']
    #             total_blockchain_model_peers_blocks += span_length
    #             initial_dict = {
    #               "peer_id": str(peer_id),
    #               "span_length": span_length,
    #               "using_relay": using_relay,
    #             }
    #             initial_blockchain_peers.append(initial_dict)
    #             break

  """bare"""
  subnet_id = 0
  authorizer = POSAuthorizer(private_key)
  # record_validator = Ed25519SignatureValidator(private_key)
  # scoring_protocol = ScoringProtocol(authorizer, "private_key.key")
  # model_report = scoring_protocol.run()
  # print("model_report", model_report)

  incentives_protocol = IncentivesProtocol(
    authorizer, 
    "private_key.key",
    RPC,
    1,
    None,
  )
  peers_data = asyncio.run(incentives_protocol.run())
  # peers_data = incentives_protocol.run()
  print("peers_data", peers_data)

  # asyncio.run(
  #   compute_peers_rps(
  #     model_stripped, 
  #     PUBLIC_INITIAL_PEERS, 
  #     subnet_id, 
  #     "private_key.key",
  #     RPC,
  #     model_report,
  #     authorizer=authorizer,
  #     record_validator=record_validator,
  #   )
  # )