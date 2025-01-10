from subnet.substrate.chain_functions import add_subnet_node, get_subnet_id_by_path
from subnet.substrate.tests.test_utils import MODEL_PATH, PEER_IDS, get_substrate_config

"""
This test requires a build with a subnet already initialized into the network pallet
"""

def test_add_subnet_nodes(count: int, path: str):
  print("adding test subnet nodes")
  substrate_config = get_substrate_config(0)
  subnet_id = get_subnet_id_by_path(
    substrate_config.interface,
    path
  )
  print("adding test subnet nodes subnet_id", subnet_id)

  for n in range(count):
    test_add_subnet_node(n, subnet_id)

def test_add_subnet_node(idx: int, subnet_id: int):
  print("test_add_subnet_node")
  substrate_config = get_substrate_config(idx)
  print("account_id: " + str(substrate_config.account_id))
  receipt = add_subnet_node(substrate_config.interface, substrate_config.keypair, subnet_id, PEER_IDS[idx], 1000e18)
  assert receipt.is_success, "add_subnet_node not successful"





if __name__ == "__main__":
  test_add_subnet_nodes(12, MODEL_PATH)