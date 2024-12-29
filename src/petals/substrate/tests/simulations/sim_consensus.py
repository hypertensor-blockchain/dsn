import asyncio
import multiprocessing as mp
from petals.substrate.tests.simulations.sim_activated_subnet import sim_activated_subnet
from petals.substrate.tests.test_utils import LOCAL_URL, MODEL_PATH, MODEL_MEMORY_MB, TestConsensus, get_substrate_config

"""
This test requires a build with a subnet already initialized into the network pallet
"""
# python src/petals/substrate/tests/simulations/sim_consensus.py

def run_consensus(subnet_node_idx: int, path: str):
    print("run_consensus")
    if asyncio.get_event_loop().is_running():
      asyncio.get_event_loop().stop()  # if we're in jupyter, get rid of its built-in event loop
      asyncio.set_event_loop(asyncio.new_event_loop())

    loop = asyncio.get_event_loop()
    print("loop")

    substrate_config = get_substrate_config(subnet_node_idx)
    print("substrate_config")
    consensus = TestConsensus(
      path=path, 
      account_id=substrate_config.account_id, 
      phrase=f"//{str(subnet_node_idx)}", 
      url=LOCAL_URL
    )

    loop.run_until_complete(consensus.run())

    async def shutdown():
      print("Stopping the event loop...")
      loop.stop()

    loop.add_signal_handler(signal.SIGTERM, lambda: loop.create_task(shutdown()))
    loop.run_forever()

def sim_consensus(path: str, memory_mb: int):
  # create activated subnet
  # add subnet nodes
  subnet_id, subnet_node_count = sim_activated_subnet(path, memory_mb)
  print("sim_consensus subnet_id        : ", subnet_id)
  print("sim_consensus subnet_node_count: ", subnet_node_count)

  assert subnet_id != 0, "Subnet not initialized with ID"

  # run consensus on each node
  processes = []
  for n in range(subnet_node_count):
    proc = mp.Process(target=run_consensus, args=(n, path,), daemon=False)
    proc.start()
    processes.append(proc)

if __name__ == "__main__":
  sim_consensus(MODEL_PATH, MODEL_MEMORY_MB)