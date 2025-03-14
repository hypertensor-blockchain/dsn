"""
A quick low resources way to benchmark a peers inference speed
Also works to loosely validate the peer is hosting the transformer blocks they say they are
"""
import pprint
import time
from typing import List, Optional
import hypermind
from hypermind import PeerID, DHT
from hypermind.utils.auth import AuthorizerBase
import numpy as np
import torch
from transformers import AutoTokenizer

from subnet.client.config import ClientConfig
from subnet.client.remote_sequential import RemoteSequential
from subnet.client.routing.sequence_manager import RemoteSequenceManager
from subnet.client.sequential_autograd import sequential_forward
from subnet.constants import DTYPE_MAP, PUBLIC_INITIAL_PEERS
from subnet.data_structures import UID_DELIMITER
from subnet.health.state_updater import ScoringProtocol
from subnet.substrate.chain_functions import get_subnet_id_by_path
from subnet.substrate.config import SubstrateConfigCustom
from subnet.utils.auto_config import AutoDistributedConfig, AutoDistributedModelForCausalLM
from subnet.utils.misc import DUMMY

from hypermind.proto import crypto_pb2
from hypermind.utils.crypto import Ed25519PrivateKey
from hypermind.utils.auth import POSAuthorizerLive, POSAuthorizer
from cryptography.hazmat.primitives.asymmetric import ed25519
import gc

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

RPC = os.getenv('LOCAL_RPC')
PHRASE = os.getenv('PHRASE')
MODEL_NAME = "bigscience/bloom-560m-petals"

# python ./src/subnet/validator/measure_compute.py

def validate_inference(
  model_name: str, 
  initial_peers: List[str], 
  subnet_id: int, 
  identity_path: str,
  rpc_url: str,
  model_report,
  authorizer: Optional[AuthorizerBase] = None,
  max_length: Optional[int] = 100,
  torch_dtype: Optional[str] = "float32",
  **kwargs,
):
  # config = AutoDistributedConfig.from_pretrained(model_name)
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
    **dict(kwargs, authorizer=authorizer)
  )

  inference_sequence_results = []
  
  for server in model_report['model_reports'][0]["server_rows"]:
    start_block = server["span"].start
    end_block = server["span"].end

    peer_id = server["peer_id"]

    config.allowed_servers = [peer_id]

    if peer_id == "12D3KooWHRgVBAYr4w56YauwnrgGG2ufF7D2LcMTrfKowm4TmneK":
      blocks = RemoteSequential(
        config, 
        dht=dht, 
        start_block=start_block,
        end_block=end_block,
        subnet_id=subnet_id,
        identity_path=identity_path,
        rpc=rpc_url
      )
    else:
      blocks = RemoteSequential(
        config, 
        dht=dht, 
        start_block=start_block,
        end_block=end_block,
        subnet_id=subnet_id,
        identity_path=identity_path,
        rpc=rpc_url
      )
    
    max_time = 5
    n_steps = 100
    warmup_steps = 5
    n_tokens = 1
    step_times = []
    device_rps = 0
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    inputs = tokenizer("A cat sat on a mat", return_tensors="pt")["input_ids"]

    random_input = torch.randn((batch_size, n_tokens, config.hidden_size))


    with torch.inference_mode():
      try:
        with blocks.inference_session(max_length=max_length) as sess:
          success = True

          for _ in range(0, n_steps):
            try:
              if _ == warmup_steps:
                start_time = time.perf_counter()
              sess.step(torch.empty(1, n_tokens, config.hidden_size), max_retries=2)
            except hypermind.p2p.p2p_daemon_bindings.utils.P2PHandlerError as e:
              success = False
              break
            except Exception as e:
              success = False
              break

          if success:
            elapsed = time.perf_counter() - start_time
            device_rps = (n_steps - warmup_steps) * n_tokens / elapsed
            inference_sequence_results.append({
              'peer_id': peer_id,
              'elapsed': elapsed,
              'device_rps': device_rps
            })
      except Exception as e:
        print("Child 1 Exception", e)


    gc.collect()
    time.sleep(0.1)

  pprint.pprint(inference_sequence_results)

  # config = ClientConfig
  
  # tokenizer = AutoTokenizer.from_pretrained(model, use_fast=False)

  # model = AutoDistributedModelForCausalLM.from_pretrained(
  #     model, initial_peers=initial_peers, torch_dtype=DTYPE_MAP[torch_dtype]
  # )

  # block_config = AutoDistributedConfig.from_pretrained(
  #   model,
  #   use_auth_token=None,
  #   revision=None,
  #   subnet_id=subnet_id,
  #   identity_path=identity_path,
  #   rpc=rpc_url,
  # )

  # device = torch.device(device)
  # if device.type == "cuda" and device.index is None:
  #     device = torch.device(device.type, index=0)

  # dummy_input = torch.randn(1, 1, block_config.hidden_size, device=device, dtype=DTYPE_MAP[torch_dtype])

  # for server in model_report["server_rows"]:
  #   start_block = server["span"].start
  #   end_block = server["span"].end

  #   block_uids = tuple(f"{config.dht_prefix}{UID_DELIMITER}{i}" for i in range(start_block, end_block))

  #   sequence_manager = RemoteSequenceManager(
  #     config, 
  #     block_uids, 
  #     dht=dht, 
  #     subnet_id=subnet_id, 
  #     identity_path=identity_path, 
  #     rpc=rpc_url, 
  #   )
  
  #   outputs, intermediate_inputs, done_sequences = sequential_forward(
  #     dummy_input,
  #     DUMMY,
  #     sequence_manager,
  #     start_block,
  #     end_index = end_block,
  #   )

  #   print("outputs \n")
  #   pprint(outputs)
  #   print("intermediate_inputs \n")
  #   pprint(intermediate_inputs)
  #   print("done_sequences \n")
  #   pprint(done_sequences)

  # peers = []
  # for peer in peers:
  #   peer_block = 
  #   with torch.inference_mode():
  #     block = get_model_block(config)
  #     block = block.to(dtype)
  #     block = convert_block(block, 0, config, tensor_parallel_devices, device, quant_type=quant_type, freeze=True)

if __name__ == "__main__":
  model_stripped = MODEL_NAME.rstrip("-petals")

  with open(f"private_key.key", "rb") as f:
    data = f.read()
    key_data = crypto_pb2.PrivateKey.FromString(data).data
    # private key stores with public because libp2p requires it as the ed25519 format
    raw_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])
    private_key = Ed25519PrivateKey(private_key=raw_private_key)

  """validator"""
  # substrate = SubstrateConfigCustom(PHRASE, RPC)
  # subnet_id = get_subnet_id_by_path(
  #   substrate.interface, 
  #   model_stripped
  # )
  # subnet_id = int(str(subnet_id))
  # print("subnet_id", subnet_id)
  # authorizer = POSAuthorizerLive(private_key, subnet_id, substrate.interface)

  """bare"""
  subnet_id = 0
  authorizer = POSAuthorizer(private_key)

  scoring_protocol = ScoringProtocol(authorizer)
  model_report = scoring_protocol.run()
  print("model_report", model_report)

  for server in model_report['model_reports'][0]["server_rows"]:
    peer_id = server["peer_id"]
    print("peer_id", peer_id)

  validate_inference(
    model_stripped, 
    PUBLIC_INITIAL_PEERS, 
    subnet_id, 
    "private_key.key",
    RPC,
    model_report,
    authorizer=authorizer,
  )