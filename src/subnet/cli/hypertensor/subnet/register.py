import argparse

from hivemind.utils.logging import get_logger

from subnet.substrate.chain_functions import get_max_subnet_registration_blocks, get_min_subnet_registration_blocks, register_subnet
from subnet.substrate.config import SubstrateConfig

logger = get_logger(__name__)


def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--path", type=str, required=True, help="Subnet ID you activated your subnet node for. ")
    parser.add_argument("--memory_mb", type=str, required=True, help="Subnet memory required to run. ")
    parser.add_argument("--registration_blocks", type=str, required=False, help="How many blocks to allow until activation. ")

    args = parser.parse_args()

    path = args.path
    memory_mb = args.memory_mb
    registration_blocks = args.registration_blocks

    min_registration_blocks = get_min_subnet_registration_blocks(SubstrateConfig.interface)
    assert registration_blocks >= min_registration_blocks, f"Registration blocks must be >= {min_registration_blocks}. "

    max_registration_blocks = get_max_subnet_registration_blocks(SubstrateConfig.interface)
    assert registration_blocks <= max_registration_blocks, f"Registration blocks must be <= {max_registration_blocks}. "

    try:
        receipt = register_subnet(
            SubstrateConfig.interface,
            SubstrateConfig.keypair,
            path,
            memory_mb,
            registration_blocks
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
