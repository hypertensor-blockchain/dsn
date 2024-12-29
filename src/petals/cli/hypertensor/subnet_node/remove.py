import argparse

from hivemind.utils.logging import get_logger

from petals.substrate.chain_functions import remove_subnet_node
from petals.substrate.config import SubstrateConfig

logger = get_logger(__name__)

"""
python -m petals.cli.hypertensor.subnet_node.remove --subnet_id 1
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you registered your subnet node for. ")

    args = parser.parse_args()

    subnet_id = args.subnet_id

    try:
        receipt = remove_subnet_node(
            SubstrateConfig.interface,
            SubstrateConfig.keypair,
            subnet_id,
        )
        logger.info(receipt)
    except Exception as e:
        logger.error("Error: ", e, exc_info=True)


if __name__ == "__main__":
    main()
