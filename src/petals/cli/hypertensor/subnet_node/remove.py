import argparse

from hivemind.utils.logging import get_logger

logger = get_logger(__name__)


def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=True, help="Subnet ID you registered your subnet node for. ")

    args = parser.parse_args()

    subnet_id = args.subnet_id

    try:
        ...
    except KeyboardInterrupt:
        ...
    finally:
        ...


if __name__ == "__main__":
    main()
