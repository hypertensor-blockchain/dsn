from petals.substrate.chain_functions import add_subnet_node, get_min_subnet_registration_blocks, get_minimum_subnet_nodes, get_subnet_data, get_subnet_id_by_path, register_subnet
from petals.substrate.tests.test_utils import MODEL_MEMORY_MB, MODEL_PATH, PEER_IDS, get_substrate_config


# python src/petals/substrate/tests/network/subnet_not_exist.py

def test_subnet_path_not_exist(path: str):
  print("test_subnet_path_not_exist")
  substrate_config = get_substrate_config(0)
  try:
    receipt = get_subnet_id_by_path(
      substrate_config.interface,
      path,
    )
    print(receipt)
  except Exception as e:
    print("Error: ", e, exc_info=True)

def test_subnet_id_not_exist(id: int):
  print("test_subnet_id_not_exist")
  substrate_config = get_substrate_config(0)
  try:
    receipt = get_subnet_data(
      substrate_config.interface,
      id,
    )
    print(receipt)
  except Exception as e:
    print("Error: ", e, exc_info=True)


if __name__ == "__main__":
  test_subnet_path_not_exist(MODEL_PATH)
  test_subnet_id_not_exist(2)