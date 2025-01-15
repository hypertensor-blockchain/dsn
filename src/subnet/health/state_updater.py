from ast import literal_eval
import datetime
import threading
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Optional

import hivemind
from hivemind.utils.auth import AuthorizerBase

from subnet.constants import TEMP_INITIAL_PEERS_LOCATION

from .config import *
from .health_v2 import fetch_health_state2, get_online_peers, get_online_peers_data, get_online_peers_data_await

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
    def __init__(self, authorizer: AuthorizerBase, **kwargs):
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
                logger.error("TEMP_INITIAL_PEERS_LOCATION error: %s" % e)

        self.dht = hivemind.DHT(
            initial_peers=initial_peers, 
            client_mode=True, 
            num_workers=32, 
            start=True,
            authorizer=authorizer
        )

    def run(self):
        try:
            state_dict = fetch_health_state2(self.dht)
            return state_dict
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