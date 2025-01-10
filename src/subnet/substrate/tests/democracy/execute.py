




import time
from subnet.substrate.chain_functions import cast_vote, execute_proposal, get_subnet_proposal, get_subnet_proposals_count
from propose import propose_activate
from subnet.substrate.tests.test_utils import PEER_IDS, get_substrate_config, BLOCK_SECS

# python src/petals/substrate/tests/democracy/execute.py
def test_execute_activate():
  receipt = propose_activate(0)
  proposal_index = 0

  count = len(PEER_IDS)

  for i in range(0, 12):
    substrate_config = get_substrate_config(i)
    cast_vote(
      substrate_config.interface,
      substrate_config.keypair,
      proposal_index,
      1000e18,
      "Yay"
    )

  substrate_config = get_substrate_config(1)
  next_props_index = get_subnet_proposals_count(substrate_config.interface)
  props_index = int(str(next_props_index)) - 1
  proposal = get_subnet_proposal(substrate_config.interface, props_index)
  max_block = proposal['max_block']

  while True:
    time.sleep(BLOCK_SECS)
    block_hash = substrate_config.interface.get_block_hash()
    block_number = substrate_config.interface.get_block_number(block_hash)
    if block_number > max_block:
      execute_proposal(
        substrate_config.interface,
        substrate_config.keypair,
        props_index,
      )
      break


if __name__ == "__main__":
  test_execute_activate()