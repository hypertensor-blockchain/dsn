"""
A copy of run_dht.py from hypermind with the ReachabilityProtocol added:
https://github.com/learning-at-home/hivemind/blob/master/hivemind/hivemind_cli/run_dht.py

This script may be used for launching lightweight CPU machines serving as bootstrap nodes to a DSN swarm.

This may be eventually merged to the hypermind upstream.
"""

import argparse
import os
import time
from secrets import token_hex
from dotenv import load_dotenv
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519

from hypermind.dht import DHT, DHTNode
from hypermind.utils.logging import get_logger, use_hypermind_log_handler
from hypermind.utils.networking import log_visible_maddrs
from hypermind.proto import crypto_pb2
from hypermind.utils.crypto import Ed25519PrivateKey
from hypermind.utils.auth import POSAuthorizerLive

from subnet.server.reachability import ReachabilityProtocol
from subnet.substrate.config import SubstrateConfigCustom

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

use_hypermind_log_handler("in_root_logger")
logger = get_logger(__name__)

async def report_status(dht: DHT, node: DHTNode):
    logger.info(
        f"{len(node.protocol.routing_table.uid_to_peer_id) + 1} DHT nodes (including this one) "
        f"are in the local routing table "
    )
    logger.debug(f"Routing table contents: {node.protocol.routing_table}")
    logger.info(f"Local storage contains {len(node.protocol.storage)} keys")
    logger.debug(f"Local storage contents: {node.protocol.storage}")

    # Contact peers and keep the routing table healthy (remove stale PeerIDs)
    await node.get(f"heartbeat_{token_hex(16)}", latest=True)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--initial_peers",
        nargs="*",
        help="Multiaddrs of the peers that will welcome you into the existing DHT. "
        "Example: /ip4/203.0.113.1/tcp/31337/p2p/XXXX /ip4/203.0.113.2/tcp/7777/p2p/YYYY",
    )
    parser.add_argument(
        "--host_maddrs",
        nargs="*",
        default=["/ip4/0.0.0.0/tcp/0", "/ip6/::/tcp/0"],
        help="Multiaddrs to listen for external connections from other DHT instances. "
        "Defaults to all IPv4 interfaces and the TCP protocol: /ip4/0.0.0.0/tcp/0",
    )
    parser.add_argument(
        "--announce_maddrs",
        nargs="*",
        help="Visible multiaddrs the host announces for external connections from other DHT instances",
    )
    parser.add_argument(
        "--use_ipfs",
        action="store_true",
        help='Use IPFS to find initial_peers. If enabled, you only need to provide the "/p2p/XXXX" '
        "part of the multiaddrs for the initial_peers "
        "(no need to specify a particular IPv4/IPv6 host and port)",
    )
    parser.add_argument(
        "--identity_path",
        type=str,
        help="Path to a private key file. If defined, makes the peer ID deterministic. "
        "If the file does not exist, writes a new private key to this file.",
    )
    parser.add_argument(
        "--no_relay",
        action="store_false",
        dest="use_relay",
        help="Disable circuit relay functionality in libp2p (see https://docs.libp2p.io/concepts/nat/circuit-relay/)",
    )
    parser.add_argument(
        "--use_auto_relay",
        action="store_true",
        help="Look for libp2p relays to become reachable if we are behind NAT/firewall",
    )
    parser.add_argument(
        "--refresh_period", type=int, default=30, help="Period (in seconds) for fetching the keys from DHT"
    )
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, help="Seed phrase for local RPC")
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you registered your subnet node for. ")

    args = parser.parse_args()
    local = args.local
    phrase = args.phrase

    if local:
        rpc = os.getenv('LOCAL_RPC')
    else:
        rpc = os.getenv('DEV_RPC')
    
    if phrase is not None:
        substrate = SubstrateConfigCustom(phrase, rpc)
    else:
        substrate = SubstrateConfigCustom(PHRASE, rpc)

    identity_path = args.identity_path
    if identity_path is not None:
        with open(f"{identity_path}", "rb") as f:
            data = f.read()
            key_data = crypto_pb2.PrivateKey.FromString(data).data
            raw_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])
            private_key = Ed25519PrivateKey(private_key=raw_private_key)

        authorizer = POSAuthorizerLive(private_key, int(args.subnet_id), substrate.interface)        

    dht = DHT(
        start=True,
        initial_peers=args.initial_peers,
        host_maddrs=args.host_maddrs,
        announce_maddrs=args.announce_maddrs,
        use_ipfs=args.use_ipfs,
        identity_path=args.identity_path,
        use_relay=args.use_relay,
        use_auto_relay=args.use_auto_relay,
        **dict(authorizer=authorizer),
    )
    log_visible_maddrs(dht.get_visible_maddrs(), only_p2p=args.use_ipfs)

    reachability_protocol = ReachabilityProtocol.attach_to_dht(dht, await_ready=True)

    while True:
        dht.run_coroutine(report_status, return_future=False)
        time.sleep(args.refresh_period)


if __name__ == "__main__":
    main()
