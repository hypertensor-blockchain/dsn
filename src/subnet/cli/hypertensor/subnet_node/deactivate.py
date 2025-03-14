import argparse

from hypermind.utils.logging import get_logger

from subnet.cli.utils.phrase_delete_print import coldkey_delete_print
from subnet.substrate.chain_functions import deactivate_subnet_node, get_hotkey_subnet_node_id
from subnet.substrate.config import SubstrateConfigCustom
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

logger = get_logger(__name__)

"""
python -m subnet.cli.hypertensor.subnet_node.deactivate --subnet_id 1
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you activated your subnet node for. ")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, required=False, help="Coldkey phrase that controls actions that include funds")

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

    subnet_id = args.subnet_id

    subnet_node_id = get_hotkey_subnet_node_id(
        substrate.interface,
        subnet_id,
        substrate.hotkey,
    )

    try:
        receipt = deactivate_subnet_node(
            substrate.interface,
            substrate.keypair,
            subnet_id,
            subnet_node_id,
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
