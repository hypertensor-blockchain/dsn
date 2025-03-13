import argparse

from hypermind.utils.logging import get_logger

from subnet.cli.utils.phrase_delete_print import coldkey_delete_print
from subnet.cli.utils.remove_last_command import remove_last_command
from subnet.substrate.chain_functions import update_hotkey
from subnet.substrate.config import SubstrateConfigCustom
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

logger = get_logger(__name__)

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--old_hotkey", type=str, required=True, help="Amount of stake to be added")
    parser.add_argument("--new_hotkey", type=str, required=True, help="Amount of stake to be added")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, required=False, help="Coldkey phrase that controls actions that include funds")

    remove_last_command()
    
    args = parser.parse_args()
    old_hotkey = args.old_hotkey
    new_hotkey = args.new_hotkey
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

    try:
        receipt = update_hotkey(
            substrate.interface,
            substrate.keypair,
            old_hotkey,
            new_hotkey,
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
