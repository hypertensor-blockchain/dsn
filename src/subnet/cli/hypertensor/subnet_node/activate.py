import argparse

from hivemind.utils.logging import get_logger

from subnet.substrate.chain_functions import activate_subnet_node
from subnet.substrate.config import SubstrateConfigCustom
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

logger = get_logger(__name__)

"""
python -m subnet.cli.hypertensor.subnet_node.activate --subnet_id 1
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you registered your subnet node for. ")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")

    args = parser.parse_args()
    local = args.local
    if local:
        rpc = os.getenv('LOCAL_RPC')
    else:
        rpc = os.getenv('DEV_RPC')

    substrate = SubstrateConfigCustom(PHRASE, rpc)

    subnet_id = args.subnet_id

    try:
        receipt = activate_subnet_node(
            substrate.interface,
            substrate.keypair,
            subnet_id,
        )
        if receipt.is_success:
            print('✅ Success, triggered events:')
            for event in receipt.triggered_events:
                print(f'* {event.value}')
        else:
            print('⚠️ Extrinsic Failed: ', receipt.error_message)
    except Exception as e:
        logger.error("Error: ", e, exc_info=True)



if __name__ == "__main__":
    main()
