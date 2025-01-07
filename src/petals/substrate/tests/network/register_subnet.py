from petals.substrate.chain_functions import add_subnet_node, get_min_subnet_registration_blocks, get_minimum_subnet_nodes, get_subnet_id_by_path, register_subnet
from petals.substrate.config import BLOCK_SECS
from petals.substrate.tests.test_utils import MODEL_MEMORY_MB, MODEL_PATH, PEER_IDS, get_substrate_config


"""
This test requires a build with a subnet already initialized into the network pallet
"""
def test_register_subnet(path: str, memory_mb: int, min_nodes: int):
  print("test_register_subnet")
  substrate_config = get_substrate_config(0)
  # minimum_subnet_nodes = get_minimum_subnet_nodes(
  #   substrate_config.interface,
  #   memory_mb,
  # )
  registration_blocks = get_min_subnet_registration_blocks(substrate_config.interface)
  print("registration_blocks", registration_blocks)

  if registration_blocks < min_nodes*BLOCK_SECS:
    registration_blocks = min_nodes*BLOCK_SECS

  try:
    receipt = register_subnet(
      substrate_config.interface,
      substrate_config.keypair,
      path,
      memory_mb,
      registration_blocks
    )
    print(receipt)
  except Exception as e:
    print("Error: ", e, exc_info=True)



if __name__ == "__main__":
  test_register_subnet(MODEL_PATH, MODEL_MEMORY_MB)