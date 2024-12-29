import time
from petals.substrate.chain_functions import get_minimum_delegate_stake, get_minimum_subnet_nodes, get_subnet_data, get_subnet_id_by_path
from petals.substrate.tests.network.activate_subnet import test_activate_subnet
from petals.substrate.tests.network.add_delegate_stakers import test_add_delegate_stakers
from petals.substrate.tests.network.add_subnet_nodes import test_add_subnet_nodes
from petals.substrate.tests.network.register_subnet import test_register_subnet
from petals.substrate.tests.test_utils import BLOCK_SECS, MODEL_MEMORY_MB, MODEL_PATH, get_substrate_config


"""
This test requires a build with a subnet already initialized into the network pallet
"""
# python src/petals/substrate/tests/simulations/sim_activated_subnet.py

def sim_activated_subnet(path: str, memory_mb: int):
  # register subnet
  test_register_subnet(path, memory_mb)
  # add nodes
  substrate_config = get_substrate_config(0)
  minimum_subnet_nodes = get_minimum_subnet_nodes(
    substrate_config.interface,
    memory_mb,
  )
  minimum_subnet_nodes = minimum_subnet_nodes['result']
  test_add_subnet_nodes(minimum_subnet_nodes, path)

  # add delegate stake balance
  subnet_id = get_subnet_id_by_path(
    substrate_config.interface,
    path
  )
  amount = get_minimum_delegate_stake(
    substrate_config.interface,
    memory_mb
  )
  test_add_delegate_stakers(subnet_id, int(amount['result']))

  subnet_data = get_subnet_data(
    substrate_config.interface,
    subnet_id
  )
  initialized = int(str(subnet_data['initialized']))
  registration_blocks = int(str(subnet_data['registration_blocks']))
  activation_block = initialized + registration_blocks
  print("activating subnet activation_block", activation_block)

  # activate
  print("activating subnet")
  while True:
    time.sleep(BLOCK_SECS)
    block_hash = substrate_config.interface.get_block_hash()
    block_number = substrate_config.interface.get_block_number(block_hash)
    print("waiting to activate subnet block_number: ", block_number)

    if block_number > activation_block:
      receipt = test_activate_subnet(subnet_id)
      print(receipt)
      break

  return subnet_id, minimum_subnet_nodes



if __name__ == "__main__":
  sim_activated_subnet(MODEL_PATH, MODEL_MEMORY_MB)