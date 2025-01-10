from substrateinterface import SubstrateInterface, Keypair
from subnet.substrate.chain_functions import add_subnet_node, add_to_delegate_stake, get_balance, get_subnet_id_by_path
from subnet.substrate.tests.test_utils import MODEL_PATH, PEER_IDS, get_substrate_config


"""
This test requires a build with a subnet already initialized into the network pallet
"""

def test_add_delegate_stakers(subnet_id: int, amount: int):

  staked_amount = 0
  n = 0
  while staked_amount < amount:
    substrate_config = get_substrate_config(n)
    balance = get_balance(
      substrate_config.interface,
      substrate_config.account_id
    )
    print("test_add_delegate_stakers balance", balance)
    balance = int(str(balance))
    if balance > 10000e18:
      balance = 10000e18
      
    add_to_delegate_stake(
      substrate_config.interface,
      substrate_config.keypair,
      subnet_id,
      balance
    )
    staked_amount += balance

if __name__ == "__main__":
  test_add_delegate_stakers(12, 1000e18)