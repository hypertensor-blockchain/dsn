import argparse

from hivemind.utils.logging import get_logger

from petals.substrate.chain_functions import remove_subnet
from petals.substrate.config import SubstrateConfig

logger = get_logger(__name__)


def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you activated your subnet node for. ")

    args = parser.parse_args()

    subnet_id = args.subnet_id

    try:
        receipt = remove_subnet(
            SubstrateConfig.interface,
            SubstrateConfig.keypair,
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
