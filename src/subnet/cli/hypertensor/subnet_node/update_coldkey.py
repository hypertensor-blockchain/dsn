import argparse

from hypermind.utils.logging import get_logger

from subnet.cli.utils.coldkey_input import coldkey_delete_print
from subnet.cli.utils.remove_last_command import remove_last_command
from subnet.substrate.chain_functions import update_coldkey
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
    parser.add_argument("--hotkey", type=str, required=True, help="Subnet node hotkey")
    parser.add_argument("--new_coldkey", type=str, required=True, help="New coldkey of subnet node")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, help="Current coldkey seed phrase being used to update the to the new coldkey")

    remove_last_command()
    
    args = parser.parse_args()
    hotkey = args.hotkey
    new_coldkey = args.new_coldkey
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
        receipt = update_coldkey(
            substrate.interface,
            substrate.keypair,
            hotkey,
            new_coldkey,
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
