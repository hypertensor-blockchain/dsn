import os
import datetime
import logging
import time
from dataclasses import asdict
from functools import partial
from typing import List

import numpy as np
from hypermind import DHT, PeerID
from hypermind.p2p.multiaddr import Multiaddr
from subnet.data_structures import UID_DELIMITER, ServerState
from subnet.utils.dht import compute_spans, get_remote_module_infos
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import *
from .p2p_utils import check_reachability_parallel, get_peers_ips, extract_peer_ip_info

logger = logging.getLogger(__name__)

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(10))
def fetch_health_state2(dht: DHT) -> dict:
    try:
        start_time = time.perf_counter()
        bootstrap_peer_ids = []
        visible_maddrs_str = dht.initial_peers
        for addr in visible_maddrs_str:
            peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
            if peer_id not in bootstrap_peer_ids:
                bootstrap_peer_ids.append(peer_id)

        reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
        bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

        model = MODEL

        logger.info(f"Fetching info for models {model}")

        block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

        module_infos = get_remote_module_infos(dht, block_uids, latest=True)

        all_servers = {}
        offset = 0
        model_servers = compute_spans(
            module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
        )
        all_servers.update(model_servers)

        offset += model.num_blocks

        online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

        reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))
        peers_info = {str(peer.peer_id): {"location": extract_peer_ip_info(str(peer.addrs[0])), "multiaddrs": [str(multiaddr) for multiaddr in peer.addrs]} for peer in dht.run_coroutine(get_peers_ips)}

        min_amount_staked = 1000e18

        model_reports = []
        block_healthy = np.zeros(model.num_blocks, dtype=bool)
        server_rows = []
        for peer_id, span in sorted(model_servers.items()):
            reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
            state = span.state.name.lower() if reachable else "unreachable"

            # only append online model validators
            if state == "online":
                block_healthy[span.start : span.end] = True
                peer_num_blocks = span.length
                """
                    Using relay shows whether a server is reachable directly or we need to 
                    use libp2p relays to traverse NAT/firewalls and reach it. Servers 
                    available through relays are usually slower, so we don't store DHT keys on them.

                    @to-do: If `using_relay` lessen score by `x%`
                """
                using_relay = span.server_info.using_relay
                """
                    score is peer_num_blocks / model_num_blocks

                    example:
                    if a peer #1 is hosting 80 out of 80 blocks they have a score of 100.0
                    if a peer #2 is hosting 20 out of 80 blocks they have a score of 20.0

                    once on the blockchain, this is summed to:
                    scores_sum: 100.0
                    peer #1 score is 80.0
                    peer #2 score is 20.0

                    we don't sum here to avoid unneccessary computations
                    the blockchains scoring mechanism is arbitrary and isn't reliant on being  `100.00`
                """
                score = int(peer_num_blocks / model.num_blocks * 1e4)
                """
                    Relay servers are slower than direct servers so we lessen the score

                    This ultimately incentivizes servers to be direct to result in a more efficient DHT
                """
                if using_relay:
                    score = int(score - score * 0.33)

                logger.info(f"Peer ID -> {peer_id}")
                logger.info(f"Score   -> {score}")

                row = {
                    "peer_id": peer_id,
                    "state": state,
                    "span": span,
                    "score": score,
                    "using_relay": using_relay,
                }
                if span.server_info.cache_tokens_left is not None:
                    # We use num_blocks * 2 to account for both keys and values
                    row["cache_tokens_left_per_block"] = span.server_info.cache_tokens_left // (span.length * 2)
                server_rows.append(row)

        model_reports.append(
            dict(
                name=model.name,
                short_name=model.short_name,
                state="healthy" if block_healthy.all() else "broken",
                server_rows=server_rows,
                model_num_blocks=model.num_blocks,
                **asdict(model),
            )
        )

        reachability_issues = [
            dict(peer_id=peer_id, err=info["error"]) for peer_id, info in sorted(reach_infos.items()) if not info["ok"]
        ]

        return dict(
            bootstrap_states=bootstrap_states,
            model_reports=model_reports,
            reachability_issues=reachability_issues,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            update_period=UPDATE_PERIOD,
            update_duration=time.perf_counter() - start_time
        )
    except Exception as e:
        logger.error(f"Error fetching peer information: {str(e)}")

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(10))
def fetch_health_state3(dht: DHT) -> dict:
    try:
        start_time = time.perf_counter()
        bootstrap_peer_ids = []
        visible_maddrs_str = dht.initial_peers
        for addr in visible_maddrs_str:
            peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
            if peer_id not in bootstrap_peer_ids:
                bootstrap_peer_ids.append(peer_id)

        reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
        bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

        model = MODEL

        logger.info(f"Fetching info for models {model}")

        block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

        module_infos = get_remote_module_infos(dht, block_uids, latest=True)

        all_servers = {}
        offset = 0
        model_servers = compute_spans(
            module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
        )
        all_servers.update(model_servers)

        logger.debug("Model Servers: ", model_servers)


        offset += model.num_blocks

        online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

        reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

        block_healthy = np.zeros(model.num_blocks, dtype=bool)
        server_rows = []
        for peer_id, span in sorted(model_servers.items()):
            reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
            state = span.state.name.lower() if reachable else "unreachable"

            # only append online model validators
            if state == "online":

                # ensure peer is in the module and using consecutive layers
                in_module = peer_in_remote_modules(peer_id, span.start, span.end, model.dht_prefix, module_infos)

                block_healthy[span.start : span.end] = True
                peer_num_blocks = span.length
                """
                    Using relay shows whether a server is reachable directly or we need to 
                    use libp2p relays to traverse NAT/firewalls and reach it. Servers 
                    available through relays are usually slower, so we don't store DHT keys on them.

                    @to-do: If `using_relay` lessen score by `x%`
                """
                using_relay = span.server_info.using_relay
                """
                    score is peer_num_blocks / model_num_blocks

                    example:
                    if a peer #1 is hosting 80 out of 80 blocks they have a score of 100.0
                    if a peer #2 is hosting 20 out of 80 blocks they have a score of 20.0

                    once on the blockchain, this is summed to:
                    scores_sum: 100.0
                    peer #1 score is 80.0
                    peer #2 score is 20.0

                    we don't sum here to avoid unneccessary computations
                    the blockchains scoring mechanism is arbitrary and isn't reliant on being  `100.00`
                """
                span_score = int(peer_num_blocks / model.num_blocks * 1e4)
                """
                    Relay servers are slower than direct servers so we lessen the score

                    This ultimately incentivizes servers to be direct to result in a more efficient DHT
                """
                if using_relay:
                    span_score = int(span_score - span_score * 0.33)

                row = {
                    "peer_id": peer_id,
                    "state": state,
                    "span": span,
                    "honest": in_module,
                    "span_score": span_score,
                    "using_relay": using_relay,
                }
                if span.server_info.cache_tokens_left is not None:
                    # We use num_blocks * 2 to account for both keys and values
                    row["cache_tokens_left_per_block"] = span.server_info.cache_tokens_left // (span.length * 2)
                server_rows.append(row)

        model_report = dict(
            name=model.name,
            short_name=model.short_name,
            state="healthy" if block_healthy.all() else "broken",
            server_rows=server_rows,
            model_num_blocks=model.num_blocks,
            **asdict(model),
        )

        reachability_issues = [
            dict(peer_id=peer_id, err=info["error"]) for peer_id, info in sorted(reach_infos.items()) if not info["ok"]
        ]

        return dict(
            bootstrap_states=bootstrap_states,
            model_report=model_report,
            reachability_issues=reachability_issues,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            update_duration=time.perf_counter() - start_time
        )
    except Exception as e:
        logger.error(f"Error fetching peer information: {str(e)}")

def peer_in_remote_modules(peer_id, start, end, dht_prefix, module_infos):
    # we later ping each block of a users span but do a quick check they're a server in each span and consecutively based on
    # the records
    for i in range(start, end):
        uid = f"{dht_prefix}{UID_DELIMITER}{i}"

        matching_module = next((module for module in module_infos if module.uid == uid), None)
        
        # If no RemoteModuleInfo matches the uid, skip the check
        if not matching_module:
            print(f"Error: No RemoteModuleInfo found for uid {uid}")
            continue

        # Validate that the peer_id is in the servers dictionary for this uid
        if peer_id not in [str(p) for p in matching_module.servers.keys()]:  # Check peer_id in servers
            print(f"Error: Peer {peer_id} is not listed in servers for {uid}")
            return False  # Return false if the peer is not found where it should be
        
    return True


@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(10))
def get_online_peers(dht: DHT) -> List:
    try:
        bootstrap_peer_ids = []
        for addr in INITIAL_PEERS:
            peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
            if peer_id not in bootstrap_peer_ids:
                bootstrap_peer_ids.append(peer_id)

        model = MODEL

        logger.info(f"Fetching online peers for model {model}")

        block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]
        module_infos = get_remote_module_infos(dht, block_uids, latest=True)

        all_servers = {}
        offset = 0
        model_servers = compute_spans(
            module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
        )
        all_servers.update(model_servers)

        offset += model.num_blocks

        online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

        return online_servers
    except Exception as e:
        logger.error(f"Error fetching online peers: {str(e)}")

def get_online_peers_data(dht: DHT) -> List:
    visible_maddrs_str = dht.initial_peers
    logger.info(f"visible_maddrs_str {visible_maddrs_str}")

    bootstrap_peer_ids = []
    for addr in visible_maddrs_str:
        peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
        if peer_id not in bootstrap_peer_ids:
            bootstrap_peer_ids.append(peer_id)
    logger.info(f"bootstrap_peer_ids {bootstrap_peer_ids}")
    # for addr in INITIAL_PEERS:
    #     peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
    #     if peer_id not in bootstrap_peer_ids:
    #         bootstrap_peer_ids.append(peer_id)

    # reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
    reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids, fetch_info=True))
    logger.info(f"reach_infos {reach_infos}")

    bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

    model = MODEL

    logger.info(f"Fetching online peers for model {model}")

    block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

    module_infos = get_remote_module_infos(dht, block_uids, latest=True)

    all_servers = {}
    offset = 0
    model_servers = compute_spans(
        module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
    )
    all_servers.update(model_servers)

    offset += model.num_blocks

    online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

    reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))
    logger.info(f"reach_infos update {reach_infos}")

    block_healthy = np.zeros(model.num_blocks, dtype=bool)
    
    peers_data = []
    for peer_id, span in sorted(model_servers.items()):
        reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
        state = span.state.name.lower() if reachable else "unreachable"
        logger.info(f"state {state} peer ID {peer_id}")
        if state == "online":
            """"""
            peer_data = {
                "peer_id": peer_id,
                "span_start": span.start,
                "span_end": span.end
            }

            peers_data.append(peer_data)

    return peers_data

"""Original implementation"""
# def get_online_peers_data(dht: DHT) -> List:
#     bootstrap_peer_ids = []
#     for addr in INITIAL_PEERS:
#         peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
#         if peer_id not in bootstrap_peer_ids:
#             bootstrap_peer_ids.append(peer_id)

#     reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))

#     bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

#     model = MODEL

#     logger.info(f"Fetching online peers for model {model}")

#     block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]
#     module_infos = get_remote_module_infos(dht, block_uids, latest=True)

#     all_servers = {}
#     offset = 0
#     model_servers = compute_spans(
#         module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
#     )
#     all_servers.update(model_servers)

#     offset += model.num_blocks

#     online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

#     reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

#     peers_data = []
#     for peer_id, span in sorted(model_servers.items()):
#         reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
#         state = span.state.name.lower() if reachable else "unreachable"

#         if state == "online":
#             """"""
#             peer_data = {
#                 "peer_id": peer_id,
#                 "span_start": span.start,
#                 "span_end": span.end
#             }

#             peers_data.append(peer_data)

#     return peers_data

# def get_online_peers_data_await(dht: DHT) -> List:
#     ready = Future()
#     async def get_p2p():
#         try:
#             bootstrap_peer_ids = []
#             common_p2p = await dht.replicate_p2p()
#             initial_peers = [str(addr) for addr in await common_p2p.get_visible_maddrs(latest=True)]

#             list_peers = await common_p2p.list_peers()
#             for info in await common_p2p.list_peers():
#                 initial_peers.extend(f"{addr}/p2p/{info.peer_id}" for addr in info.addrs)
#                 # if info.peer_id not in bootstrap_peer_ids:
#                 #     bootstrap_peer_ids.append(info.peer_id)

#                 # peer_id = PeerID.to_bytes(info.peer_id)

#                 # peer_id = PeerID.from_base58(Multiaddr(info.peer_id)["p2p"])
#                 if info.peer_id not in bootstrap_peer_ids:
#                     bootstrap_peer_ids.append(info.peer_id)

#             reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))

#             bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

#             model = MODEL

#             logger.info(f"Fetching online peers for model {model}")

#             block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

#             module_infos = get_remote_module_infos(dht, block_uids, latest=True)


#             all_servers = {}
#             offset = 0
#             model_servers = compute_spans(
#                 module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
#             )
#             all_servers.update(model_servers)

#             offset += model.num_blocks

#             online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

#             reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

#             peers_data = []
#             for peer_id, span in sorted(model_servers.items()):
#                 reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
#                 state = span.state.name.lower() if reachable else "unreachable"

#                 if state == "online":
#                     """"""
#                     peer_data = {
#                         "peer_id": peer_id,
#                         "span_start": span.start,
#                         "span_end": span.end
#                     }

#                     peers_data.append(peer_data)

#             return peers_data
#         except Exception as e:
#             print("get_p2p error", e)
#             return []


#     threading.Thread(target=partial(asyncio.run, get_p2p()), daemon=True).start()


# def get_online_peers_data_await(dht: DHT) -> List:
#     i_peers = dht.initial_peers
#     ready = Future()
#     async def get_p2p():
#         try:
#             bootstrap_peer_ids = []
#             common_p2p = await dht.replicate_p2p()
#             initial_peers = [str(addr) for addr in await common_p2p.get_visible_maddrs(latest=True)]

#             for addr in initial_peers:
#                 peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
#                 if peer_id not in bootstrap_peer_ids:
#                     bootstrap_peer_ids.append(peer_id)

#             reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))

#             bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

#             model = MODEL

#             logger.info(f"Fetching online peers for model {model}")

#             block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

#             module_infos = get_remote_module_infos(dht, block_uids, latest=True)

#             all_servers = {}
#             offset = 0
#             model_servers = compute_spans(
#                 module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
#             )
#             all_servers.update(model_servers)

#             offset += model.num_blocks

#             online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

#             reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

#             peers_data = []
#             for peer_id, span in sorted(model_servers.items()):
#                 reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
#                 state = span.state.name.lower() if reachable else "unreachable"

#                 if state == "online":
#                     """"""
#                     peer_data = {
#                         "peer_id": peer_id,
#                         "span_start": span.start,
#                         "span_end": span.end
#                     }

#                     peers_data.append(peer_data)

#             return peers_data
#         except Exception as e:
#             print("get_p2p error", e)
#             return []


#     threading.Thread(target=partial(asyncio.run, get_p2p()), daemon=True).start()

def get_online_peers_data_await(dht: DHT) -> List:
    try:
        initial_peers = dht.initial_peers
        logger.info(f"initial_peers {initial_peers}")

        bootstrap_peer_ids = []
        for addr in initial_peers:
            peer_id = PeerID.from_base58(Multiaddr(addr)["p2p"])
            if peer_id not in bootstrap_peer_ids:
                bootstrap_peer_ids.append(peer_id)

        logger.info(f"bootstrap_peer_ids {bootstrap_peer_ids}")

        reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
        logger.info(f"reach_infos {reach_infos}")

        # bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

        model = MODEL

        logger.info(f"Fetching online peers for model {model}")

        block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for i in range(model.num_blocks)]

        module_infos = get_remote_module_infos(dht, block_uids, latest=True)
        logger.info(f"module_infos {module_infos}")

        all_servers = {}
        offset = 0
        model_servers = compute_spans(
            module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
        )
        all_servers.update(model_servers)

        offset += model.num_blocks

        online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]

        reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

        peers_data = []
        for peer_id, span in sorted(model_servers.items()):
            reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
            state = span.state.name.lower() if reachable else "unreachable"
            logger.info(f"state {state} peer ID {peer_id}")
            if state == "online":
                """"""
                peer_data = {
                    "peer_id": peer_id,
                    "span_start": span.start,
                    "span_end": span.end
                }

                peers_data.append(peer_data)

        return peers_data
    except Exception as e:
        logger.error("Fetch online peers error: %s", e, exc_info=True)
    finally:
        return []
