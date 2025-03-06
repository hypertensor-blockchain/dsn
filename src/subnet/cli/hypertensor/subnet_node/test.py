import argparse
from hypermind.utils.logging import get_logger

from pathlib import Path
import os
from dotenv import load_dotenv

from subnet.cli.utils.coldkey_input import coldkey_delete_print, coldkey_input
from subnet.cli.utils.remove_last_command_v2 import remove_last_command

load_dotenv(os.path.join(Path.cwd(), '.env'))

PHRASE = os.getenv('PHRASE')

logger = get_logger(__name__)

"""
python -m subnet.cli.hypertensor.subnet_node.test --subnet_id 1
"""

def main():
    # fmt:off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--subnet_id", type=str, required=False, help="Subnet ID stored on blockchain. ")

    args = parser.parse_args()

    if args.subnet_id:
        remove_last_command()

    if args.subnet_id:
        coldkey_input()

    coldkey_delete_print()
    
if __name__ == "__main__":
    main()
