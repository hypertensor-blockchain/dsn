from ast import literal_eval
from functools import partial
import math
from typing import Any, Dict, List, Optional
import torch

import hivemind
from hivemind.utils.auth import AuthorizerBase
from hivemind import PeerID
from hivemind.utils import DHTExpiration, get_dht_time
from hivemind.dht.routing import DHTKey
from hivemind.utils.crypto import Ed25519PrivateKey, Ed25519PublicKey
from hivemind.dht import DHTNode
from hivemind.dht.crypto import Ed25519SignatureValidator, RecordValidatorBase
from hivemind.proto import crypto_pb2
from hivemind.utils.crypto import Ed25519PrivateKey

from cryptography.hazmat.primitives.asymmetric import ed25519

from subnet.client.remote_sequential import RemoteSequential
from subnet.constants import TEMP_INITIAL_PEERS_LOCATION
from subnet.server.throughput import synchronize
from subnet.substrate.chain_data import SubnetNode
from subnet.utils.auto_config import AutoDistributedConfig

from subnet.health.config import *
from subnet.health.health_v2 import fetch_health_state3

from subnet.substrate.config import SubstrateConfigCustom
# from subnet.substrate.utils import get_blockchain_included
from subnet.substrate.chain_functions import get_epoch_length

logger = hivemind.get_logger(__name__)

class IncentivesProtocol():
    """
    Calculates each nodes score based on speed and blocks hosted
    """
    def __init__(
        self, 
        authorizer: AuthorizerBase, 
        identity_path: Optional[str], 
        rpc_url: Optional[str],
        subnet_id: Optional[int],
        substrate: Optional[SubstrateConfigCustom] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        initial_peers = INITIAL_PEERS
        if initial_peers is None or len(initial_peers) == 0:
            try:
                """
                In the case where the first node has no ``initial_peers`` we can use themselves as the initial peer
                if they are hosting the entire model, otherwise they will need to wait for others to join
                """
                f = open(TEMP_INITIAL_PEERS_LOCATION, "r")
                f_initial_peers = f.read()
                f_initial_peers_literal_eval = literal_eval(f_initial_peers)
                f_initial_peers_tuple = tuple(f_initial_peers_literal_eval)
                initial_peers = f_initial_peers_tuple
            except Exception as e:
                logger.warning("TEMP_INITIAL_PEERS_LOCATION error: %s" % e)

        self.subnet_id = subnet_id
        self.substrate = substrate
        self.identity_path = identity_path
        with open(f"{self.identity_path}", "rb") as f:
            data = f.read()
            key_data = crypto_pb2.PrivateKey.FromString(data).data
            raw_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])
            private_key = Ed25519PrivateKey(private_key=raw_private_key)

        self.record_validator = Ed25519SignatureValidator(private_key)
        self.rpc_url = rpc_url
        self.epoch_length = 0 if self.substrate is None else int(str(get_epoch_length(self.substrate.interface)))

        self.dht = hivemind.DHT(
            initial_peers=initial_peers, 
            client_mode=True, 
            num_workers=32, 
            start=True,
            record_validators=[self.record_validator],
            **dict(kwargs, authorizer=authorizer)
        )

    async def run(self) -> Dict:
        try:
            state_dict = self.get_health_state()
            if state_dict == None:
                return {
                    "model_state": "broken",
                    "peers": []
                }
            
            state_dict = self.clean_model_report(state_dict)
            
            """Try to get the speed scores"""
            try:
                state_dict = await self.get_rps(state_dict)
            except Exception as e:
                logger.warning("Incentives Protocol Error: ", e)
                pass

            return state_dict
        except:
            return None
        
    def clean_model_report(self, state_dict) -> List:
        """
        Removes any peer_ids that don't match the blockchains subnet nodes
        """
        # watch for circular import on testing with measure compute
        # subnet_nodes = get_blockchain_included(self.substrate, self.subnet_id)
        subnet_nodes = [
            SubnetNode(
                account_id="",
                hotkey="",
                peer_id="12D3KooWHRgVBAYr4w56YauwnrgGG2ufF7D2LcMTrfKowm4TmneK",
                initialized=0,
                classification="0",
                a="0",
                b="0",
                c="0"
            ),
            SubnetNode(
                account_id="",
                hotkey="",
                peer_id="12D3KooWMRSF23cFaFPTM9YTz712BSntSY5WmA88Db12E9NqtT8S",
                initialized=0,
                classification="0",
                a="0",
                b="0",
                c="0"
            ),
        ]
        subnet_nodes = {node.peer_id for node in subnet_nodes}
        state_dict["model_report"]["server_rows"] = [
            row for row in state_dict["model_report"]["server_rows"] if row["peer_id"] in subnet_nodes
        ]
        return state_dict

    def get_health_state(self):
        state_dict = fetch_health_state3(self.dht)
        return state_dict

    async def get_rps(self, state_dict):
        """
        Measures the inference RPS per peer in subnet
        """
        config = AutoDistributedConfig.from_pretrained(
            "Orenguteng/Llama-3.1-8B-Lexi-Uncensored-V2",
            subnet_id=self.subnet_id,
            identity_path=self.identity_path,
            rpc=self.rpc_url,
        )
        num_blocks = state_dict['model_report']['num_blocks']
        times = []
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        device = torch.device(device)

        for server in state_dict["model_report"]["server_rows"]:
            start_block = server["span"].start
            end_block = server["span"].end
            peer_id = server["peer_id"]
            config.allowed_servers = [peer_id]

            blocks = RemoteSequential(
                config, 
                dht=self.dht, 
                start_block=start_block,
                end_block=end_block,
                subnet_id=self.subnet_id,
                identity_path=self.identity_path,
                rpc=self.rpc_url
            )

            blocks_served_ratio = (end_block - start_block) / num_blocks
            n_steps = 24
            n_steps = max(n_steps, int(n_steps / blocks_served_ratio))
            scaling_factor1 = math.pow(blocks_served_ratio, 1-math.sqrt(blocks_served_ratio))
            scaling_factor = (blocks_served_ratio / scaling_factor1)
            
            max_length = 100
            max_length = max(n_steps, max_length)  

            warmup_steps = 5
            n_tokens = 1

            rps_data = await self.measure_inference_steps(
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

            if rps_data is not None:
                server.update(rps_data)

        epoch = self.get_epoch()
        key = b"".join([b"rps", str(epoch).encode()])  
        subkey = b"protected_subkey" + self.record_validator.local_public_key

        expiration_time = get_dht_time()+10
        self.dht.run_coroutine(
            partial(_store_rps, key=key, subkey=subkey, value=times, expiration_time=expiration_time),
            return_future=False,
        )

        return state_dict

    async def measure_inference_steps(
        self,
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
    ) -> List:
        timed_result = None
        time_steps = []
        device = torch.device(device)
        with torch.inference_mode():
            synchronize(device)
            torch.manual_seed(42)  
            with blocks.inference_session(max_length=max_length) as sess:
                success = True
                for _ in range(0, n_steps):
                    try:
                        time, outputs = sess.timed_step(torch.empty(1, n_tokens, config.hidden_size), max_retries=0)
                        if _ >= warmup_steps:
                            time_steps.append(time)
                    except hivemind.p2p.p2p_daemon_bindings.utils.P2PHandlerError as e:
                        logger.warning(f"RPS Exception {e}", exc_info=True)
                        success = False
                        break
                    except Exception as e:
                        logger.warning(f"RPS Exception {e}", exc_info=True)
                        success = False
                        break
                    
                if success:
                    elapsed = sum(time_steps)
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
                        'blocks_served_ratio': blocks_served_ratio,
                        'steps': n_steps,
                    }
        synchronize(device)
        return timed_result
    
    def calculate_rps_data(self, state_dict, epoch: int):
        # get previous epochs rps data
        epoch = self.get_epoch() - 1
        key = b"".join([b"rps", str(epoch).encode()])  

        rps_get = self.dht.run_coroutine(
            partial(
                _get_rps,
                key=key,
                expiration_time=math.inf,
                latest=True,
            ),
            return_future=False,
        )

        for server in state_dict["model_report"]["server_rows"]:
            peer_id = server["peer_id"]
        for v in rps_get[key]:
            try:
                if isinstance(v, dict):
                    print("rps_get k", v.keys())
                    print("rps_get v", v.values())
                    subkeys = list(v.keys())
                    for subkey in subkeys:
                        peer_id = extract_peer_id(self.record_validator, subkey)
                        print("rps_get peer_id", peer_id)
            except Exception as e:
                print(e)

    def get_score(self):
        ...

    def get_epoch(self) -> int:
        if self.substrate is not None:
            return 1
        return 1

async def _store_rps(
    dht: hivemind.DHT,
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

async def _get_rps(
    dht: hivemind.DHT,
    node: DHTNode,
    key: Any,
    expiration_time: Optional[DHTExpiration],
    latest: bool,
) -> Any:
    found = await node.get_many([key], expiration_time)
    return found

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
