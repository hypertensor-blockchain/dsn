import argparse
from hypermind.utils.logging import get_logger

from subnet.cli.utils.phrase_delete_print import coldkey_delete_print
from subnet.substrate.chain_functions import register_subnet_node
from subnet.substrate.config import SubstrateConfigCustom
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

logger = get_logger(__name__)

"""
python -m subnet.cli.hypertensor.subnet_node.register --subnet_id 1 --peer_id 12D3KooWBF38f6Y9NE4tMUQRfQ7Yt2HS26hnqUTB88isTZF8bwLs --stake_to_be_added 1000.00 
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID stored on blockchain. ")
    parser.add_argument("--hotkey", type=str, required=False, help="Hotkey responsible for subnet features. ")
    parser.add_argument("--peer_id", type=str, required=True, help="Peer ID generated using `keygen`")
    parser.add_argument("--bootstrap_peer_id", type=str, required=False, default=None, help="Bootstrap Peer ID generated using `keygen`")
    parser.add_argument("--delegate_reward_rate", type=float, required=False, default=0.0, help="Reward weight for your delegate stakers")
    parser.add_argument("--stake_to_be_added", type=float, required=True, help="Amount of stake to be added")
    parser.add_argument("--b", type=str, required=False, default=None, help="Non-unique value for subnet node")
    parser.add_argument("--c", type=str, required=False, default=None, help="Non-unique value for subnet node")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, required=False, default="PHRASE", help="Phrase env title")

    args = parser.parse_args()
    local = args.local
    phrase = args.phrase
    hotkey = args.hotkey

    if not args.hotkey:
        confirm = input(
            f"Are you sure you want to proceed with using the same key for both hotkey and coldkey? "
            f"The hotkey is used for frequent operations such as validating and attesting and can be updated by the coldkey. "
            f"The coldkey is used for any operations including the movement of tokens. "
            f"Are you sure you want to proceed? (yes/no): "
            ).strip().lower()
        if confirm not in ["yes", "y"]:
            print("Must be yes or y, action canceled.")
            return

    if local:
        rpc = os.getenv('LOCAL_RPC')
    else:
        rpc = os.getenv('DEV_RPC')

    if phrase is not None:
        substrate = SubstrateConfigCustom(phrase, rpc)
    else:
        substrate = SubstrateConfigCustom(PHRASE, rpc)

    if hotkey is None:
        hotkey = substrate.keypair.ss58_address

    subnet_id = args.subnet_id
    peer_id = args.peer_id
    delegate_reward_rate = int(args.delegate_reward_rate * 1e9)
    stake_to_be_added = int(args.stake_to_be_added * 1e18)
    bootstrap_peer_id = args.bootstrap_peer_id
    b = args.b
    c = args.c

    try:
        receipt = register_subnet_node(
            substrate.interface,
            substrate.keypair,
            subnet_id,
            hotkey,
            peer_id,
            delegate_reward_rate,
            stake_to_be_added,
            bootstrap_peer_id,
            None,
            None
        )
        if receipt.is_success:
            print('✅ Success, triggered events:')
            for event in receipt.triggered_events:
                print(f'* {event.value}')
        else:
            print('⚠️ Extrinsic Failed: ', receipt.error_message)
    except Exception as e:
        logger.error("Error: ", e, exc_info=True)

    if phrase:
        coldkey_delete_print()

if __name__ == "__main__":
    main()
