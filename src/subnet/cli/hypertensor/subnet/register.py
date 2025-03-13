import argparse

from hypermind.utils.logging import get_logger

from subnet.substrate.chain_functions import get_max_subnet_entry_interval, get_max_subnet_registration_blocks, get_min_subnet_registration_blocks, register_subnet
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
    parser.add_argument("--path", type=str, required=True, help="Subnet ID you activated your subnet node for. ")
    parser.add_argument("--memory_mb", type=int, required=True, help="Subnet memory required to run. ")
    parser.add_argument("--registration_blocks", type=int, required=False, help="How many blocks to allow until activation. ")
    parser.add_argument("--entry_interval", type=int, required=False, help="Blocks between each subnet node entry. ")
    parser.add_argument("--local", action="store_true", help="Run in local mode, uses LOCAL_RPC")
    parser.add_argument("--phrase", type=str, help="Seed phrase for local RPC")

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

    path = args.path
    memory_mb = args.memory_mb
    registration_blocks = args.registration_blocks
    entry_interval = args.entry_interval

    if registration_blocks == 0:
        registration_blocks = int(str(get_min_subnet_registration_blocks(substrate.interface)))
    else:
        min_registration_blocks = int(str(get_min_subnet_registration_blocks(substrate.interface)))
        assert registration_blocks >= min_registration_blocks, f"Registration blocks must be >= {min_registration_blocks}. "

        max_registration_blocks = int(str(get_max_subnet_registration_blocks(substrate.interface)))
        assert registration_blocks <= max_registration_blocks, f"Registration blocks must be <= {max_registration_blocks}. "

    if entry_interval != 0:
        max_entry_interval = get_max_subnet_entry_interval(substrate.interface)
        assert entry_interval <= max_entry_interval, f"Entry interval blocks must be <= {max_entry_interval}. "

    try:
        receipt = register_subnet(
            substrate.interface,
            substrate.keypair,
            path,
            memory_mb,
            registration_blocks,
            entry_interval,
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
