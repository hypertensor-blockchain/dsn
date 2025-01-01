from petals.substrate.chain_functions import activate_subnet
from petals.substrate.tests.test_utils import get_substrate_config

def test_activate_subnet(subnet_id: int):
  print("test_register_subnet")
  substrate_config = get_substrate_config(0)
  try:
    receipt = activate_subnet(
      substrate_config.interface,
      substrate_config.keypair,
      subnet_id,
    )
    print("test_activate_subnet receipt", receipt)
    return receipt
  except Exception as e:
    print("Error: ", e, exc_info=True)
    return(e)