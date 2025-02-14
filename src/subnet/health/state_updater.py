from ast import literal_eval
import datetime
from functools import partial
import math
import threading
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import hivemind
from hivemind.utils.auth import AuthorizerBase
import numpy as np
import torch
from hivemind import PeerID
from hivemind.utils import DHTExpiration, get_dht_time
from hivemind.dht.routing import DHTKey
from hivemind.utils.crypto import Ed25519PrivateKey, Ed25519PublicKey
from hivemind.dht import DHTNode
from hivemind.dht.crypto import Ed25519SignatureValidator, RecordValidatorBase

from cryptography.hazmat.primitives.asymmetric import ed25519

from subnet.client.remote_sequential import RemoteSequential
from subnet.constants import TEMP_INITIAL_PEERS_LOCATION
from subnet.server.throughput import synchronize
from subnet.substrate.chain_data import SubnetNode
from subnet.substrate.chain_functions import get_epoch_length
from subnet.utils.auto_config import AutoDistributedConfig
from subnet.utils.math_utils import remove_outliers_adaptive, remove_outliers_iqr

from .config import *
from .health_v2 import fetch_health_state2, fetch_health_state3, get_online_peers, get_online_peers_data, get_online_peers_data_await
from hivemind.proto import crypto_pb2
from hivemind.utils.crypto import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import ed25519

from subnet.substrate.config import SubstrateConfigCustom

logger = hivemind.get_logger(__name__)

# python src/subnet/health/state_updater.py

class StateUpdaterThread(threading.Thread):
    def __init__(self, dht: hivemind.DHT, **kwargs):
        super().__init__(**kwargs)
        self.dht = dht
        # self.app = app

        self.state_json = self.state_html = None
        self.ready = threading.Event()

    def run(self):
        start_time = time.perf_counter()
        # try:
        #     # state_dict = fetch_health_state(self.dht)
        #     state_dict = fetch_health_state2(self.dht)

        #     self.state_json = simplejson.dumps(state_dict, indent=2, ignore_nan=True, default=json_default)

        #     # self.ready.set()
        #     logger.info(f"Fetched new state in {time.perf_counter() - start_time:.1f} sec")
        # except Exception:
        #     logger.error("Failed to update state:", exc_info=True)
        # self.exit()

    # def run(self):
    #     while True:
    #         start_time = time.perf_counter()
    #         try:
    #             # state_dict = fetch_health_state(self.dht)
    #             state_dict = fetch_health_state2(self.dht)

    #             self.state_json = simplejson.dumps(state_dict, indent=2, ignore_nan=True, default=json_default)

    #             self.ready.set()
    #             logger.info(f"Fetched new state in {time.perf_counter() - start_time:.1f} sec")
    #         except Exception:
    #             logger.error("Failed to update state:", exc_info=True)

    #         delay = UPDATE_PERIOD - (time.perf_counter() - start_time)
    #         if delay < 0:
    #             logger.warning("Update took more than update_period, consider increasing it")
    #         time.sleep(max(delay, 0))

class ScoringProtocol():
    def __init__(self, authorizer: AuthorizerBase, identity_path: Optional[str], **kwargs):
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

        with open(f"{identity_path}", "rb") as f:
            data = f.read()
            key_data = crypto_pb2.PrivateKey.FromString(data).data
            # private key stores with public because libp2p requires it as the ed25519 format
            raw_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])
            private_key = Ed25519PrivateKey(private_key=raw_private_key)

        record_validator = Ed25519SignatureValidator(private_key)

        self.dht = hivemind.DHT(
            initial_peers=initial_peers, 
            client_mode=True, 
            num_workers=32, 
            start=True,
            record_validators=[record_validator],
            authorizer=authorizer
        )

    def run(self):
        try:
            state_dict = fetch_health_state3(self.dht)
            return state_dict
        except:
            return None

BLOCK_WEIGHT = 0.5
RPS_WEIGHT = 1 - BLOCK_WEIGHT

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
            print("state_dict 1: ", state_dict)

            if state_dict == None:
                return {
                    "model_state": "broken",
                    "peers": []
                }
            
            state_dict = self.clean_model_report(state_dict)

            """Try to get the speed scores"""
            try:
                state_dict = await self.measure_rps(state_dict)
                # print("state_dict measure_rps", state_dict)

                epoch = self.get_epoch()
                calculated_rps = self.calculate_rps_data(state_dict, epoch)
                # print("state_dict calculated_rps", calculated_rps)
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
        subnet_nodes = [node.peer_id for node in subnet_nodes]
        state_dict["model_report"]["server_rows"] = [
            row for row in state_dict["model_report"]["server_rows"] if row["peer_id"] in subnet_nodes
        ]
        return state_dict

    def get_health_state(self):
        state_dict = fetch_health_state3(self.dht)
        return state_dict

    async def measure_rps(self, state_dict):
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
        """
        Measure each nodes RPS using empty tensors and store signed DHTRecord

        Args:
            blocks (RemoteSequential): Remote Sequential class set up for blocks node is hosting
            device (torch.device):
            peer_id (PeerID): Peer ID
            start_block (int): Start block
            end_block (int): End block
            blocks_served_ratio (float): Percentage of blocks node is hosting
            scaling_factor (float):
            max_length (int): Max length of session
            n_steps (int):
            warmup_steps (int): Steps to not count in RPS for warming up servers
            n_tokens (int):
            config
        """
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
                
                print("time_steps", time_steps)
                if success:
                    # Compute lower bound to 0 before running IQR
                    Q1 = np.percentile(time_steps, 25)
                    Q3 = np.percentile(time_steps, 75)
                    IQR = Q3 - Q1
                    lower_multiplier = Q1 / IQR

                    print("len(time_steps)", len(time_steps))
                    
                    # Remove upper bound only to remove server anomalies
                    filtered_time_steps = remove_outliers_iqr(time_steps, lower_multiplier=lower_multiplier) # remove outliers
                    print("len(filtered_time_steps)", len(filtered_time_steps))
                    avg = np.mean(filtered_time_steps)
                    print("time step average", avg)
                    avg_elapsed = (n_steps - warmup_steps) * avg
                    print("avg_elapsed", avg_elapsed)
                    if blocks_served_ratio != 1.0:
                        avg_device_rps = (n_steps - warmup_steps) * n_tokens / avg_elapsed * scaling_factor
                    else:
                        avg_device_rps = (n_steps - warmup_steps) * n_tokens / avg_elapsed
                    print("avg_device_rps", avg_device_rps)

                    elapsed = sum(time_steps)
                    if blocks_served_ratio != 1.0:
                        device_rps = ((n_steps - warmup_steps) * n_tokens) / elapsed * scaling_factor
                    else:
                        device_rps = (n_steps - warmup_steps) * n_tokens / elapsed
                    print("device_rps", device_rps)

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
        """
        Get DHTRecord from epoch and calculate RPS
        Use IQR algorithm to calculate each nodes RPS results from each node

        Args:
            state_dict (dict): Dictionary of all nodes in subnet and on blockchain.
            epoch (int): The current epoch.
        """

        # get previous epochs rps data
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

        model_report = state_dict.get("model_report", None)
        if model_report is None:
            return 
        
        server_rows = model_report.get("server_rows", None)
        if server_rows is None:
            return 

        # Use a list comprehension to extract peer_ids
        chain_peers = [
            {"peer_id": str(server_row["peer_id"]), "device_rps_list": []}
            for server_row in server_rows
        ]

        inner_dict = rps_get[key].value
        for subnet_node in chain_peers:
            for subkey, values in inner_dict.items():
                data_entry_peer_id = extract_peer_id(self.record_validator, subkey)
                exists = any(row["peer_id"] == data_entry_peer_id for row in state_dict["model_report"]["server_rows"])
                if not exists:
                    continue

                for value in values.value:
                    if subnet_node["peer_id"] == value['peer_id']:
                        subnet_node["device_rps_list"].append(value['device_rps'])

        for server in state_dict["model_report"]["server_rows"]:
            peer_id = server["peer_id"]
            for subnet_node in chain_peers:
                if subnet_node["peer_id"] == peer_id:
                    device_rps_list = subnet_node["device_rps_list"]
                    filtered_rps_list = remove_outliers_adaptive(device_rps_list)
                    rps = np.mean(filtered_rps_list)
                    print("rps np.mean", rps)
                    server["rps"] = rps
                    break

    def get_score(self, state_dict):
        """
        Uses the block weight and rps weight to determine each nodes score
        """
        num_blocks = state_dict['model_report']['num_blocks']
        node_count = len(state_dict["model_report"]["server_rows"])
        num_blocks_sum = num_blocks * node_count
        rps_sum = sum(row.get("rps", 0) for row in state_dict["model_report"]["server_rows"])
        for server in state_dict["model_report"]["server_rows"]:
            peer_id = server["peer_id"]
            rps = server["rps"]
            rps_weight = int(rps / rps_sum * 1e4)
            span_weight = server["span"].end - server["span"].start
            transformer_block_weight = int(span_weight / num_blocks_sum * 1e4)
            weight = rps_weight * RPS_WEIGHT + transformer_block_weight * BLOCK_WEIGHT

            
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

def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.name.lower()
    if isinstance(value, hivemind.PeerID):
        return value.to_base58()
    if isinstance(value, datetime.datetime):
        return value.timestamp()
    raise TypeError(f"Can't serialize {repr(value)}")

# def get_peers_data():
#     dht = hivemind.DHT(initial_peers=INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
#     # updater = StateUpdaterThread(dht, daemon=True)
#     # updater.start()
#     # updater.ready.wait()
#     state_dict = fetch_health_state2(dht)
#     return state_dict

def get_peers_data():
    try:
        dht = hivemind.DHT(initial_peers=INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
        # updater = StateUpdaterThread(dht, daemon=True)
        # updater.start()
        # updater.ready.wait()
        state_dict = fetch_health_state2(dht)
        return state_dict
    except Exception as error:
        logger.error("Failed to get peers data:", error)
        return None

def get_peer_ids_list():
    try:
        dht = hivemind.DHT(initial_peers=INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
        # updater = StateUpdaterThread(dht, daemon=True)
        # updater.start()
        # updater.ready.wait()
        state_dict = get_online_peers(dht)
        return state_dict
    except Exception as error:
        logger.error("Failed to get peers list:", error)
        return None

def get_peers_data_list(authorizer: Optional[AuthorizerBase] = None):
    try:
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
                logger.error("TEMP_INITIAL_PEERS_LOCATION error: %s" % e)

        dht = hivemind.DHT(
            initial_peers=initial_peers, 
            client_mode=True, 
            num_workers=32, 
            start=True,
            authorizer=authorizer
        )
        state_dict = get_online_peers_data(dht)
        return state_dict
    except Exception as error:
        logger.error("Failed to get peers list:", error)
        return None
    
def get_peers_scores(authorizer: Optional[AuthorizerBase] = None):
    try:
        initial_peers = INITIAL_PEERS
        if initial_peers is None or len(initial_peers) == 0:
            try:
                """
                In the case where the first node has no ``initial_peers`` we can use themselves as the initial peer
                if they are hosting the entire model, otherwise they will need to wait for others to join
                """
                f = open(TEMP_INITIAL_PEERS_LOCATION, "r")
                f_initial_peers = f.read()
                print("f_initial_peers", f_initial_peers)
                f_initial_peers_literal_eval = literal_eval(f_initial_peers)
                f_initial_peers_tuple = tuple(f_initial_peers_literal_eval)
                initial_peers = f_initial_peers_tuple
            except Exception as e:
                logger.error("TEMP_INITIAL_PEERS_LOCATION error: %s" % e, exc_info=True)

        dht = hivemind.DHT(
            initial_peers=initial_peers, 
            client_mode=True, 
            num_workers=32, 
            start=True,
            authorizer=authorizer
        )
        state_dict = fetch_health_state2(dht)
        return state_dict
    except Exception as error:
        logger.error("Failed to get peers list:", error)
        return None


def get_peers_data_list_with_dht(dht: hivemind.DHT):
    try:
        state_dict = get_online_peers_data_await(dht)
        # dht = hivemind.DHT(initial_peers=INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
        # state_dict = get_online_peers_data(dht)

        return state_dict
    except Exception as error:
        logger.error("Failed to get peers list:", error)
        return None