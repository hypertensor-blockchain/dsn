import argparse

from hivemind.utils.logging import get_logger

from subnet.substrate.chain_functions import deactivate_subnet_node
from subnet.substrate.config import SubstrateConfig

logger = get_logger(__name__)

"""
python -m petals.cli.hypertensor.subnet_node.deactivate --subnet_id 1
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you activated your subnet node for. ")

    args = parser.parse_args()

    subnet_id = args.subnet_id

    try:
        receipt = deactivate_subnet_node(
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
