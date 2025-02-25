import asyncio
import multiprocessing as mp
import signal
from subnet.substrate.config import SubstrateConfigCustom
# from subnet.substrate.consensus import Consensus
from subnet.substrate.tests.simulations.sim_register_subnet import sim_register_subnet
from subnet.substrate.tests.test_utils import LOCAL_URL, MODEL_PATH, MODEL_MEMORY_MB, Consensus
from hypermind.utils.auth import POSAuthorizerLive
from cryptography.hazmat.primitives.asymmetric import ed25519
from hypermind.utils.crypto import Ed25519PrivateKey, Ed25519PublicKey

"""
This test requires a build with a subnet already initialized into the network pallet
"""
# python src/subnet/substrate/tests/simulations/sim_consensus.py

def run_consensus(subnet_node_idx: int, path: str, subnet_id: int):
    print("run_consensus")
    if asyncio.get_event_loop().is_running():
      asyncio.get_event_loop().stop()  # if we're in jupyter, get rid of its built-in event loop
      asyncio.set_event_loop(asyncio.new_event_loop())

    loop = asyncio.get_event_loop()
    print("loop")

    print("substrate_config")
    # consensus = TestConsensus(
    #   path=path, 
    #   substrate=SubstrateConfigCustom(f"//{str(subnet_node_idx)}", LOCAL_URL)
    # )

    # private_key = ed25519.Ed25519PrivateKey.generate()
    # private_key = Ed25519PrivateKey(private_key=private_key)

    # substrate = SubstrateConfigCustom(f"//{str(subnet_node_idx)}", LOCAL_URL)
    # authorizer = POSAuthorizerLive(private_key, subnet_id, substrate.interface)

    consensus = Consensus(
      path=path, 
      authorizer=None,
      substrate=SubstrateConfigCustom(f"//{str(subnet_node_idx)}", LOCAL_URL)
    )

    loop.run_until_complete(consensus.start())

    async def shutdown():
      print("Stopping the event loop...")
      loop.stop()

    loop.add_signal_handler(signal.SIGTERM, lambda: loop.create_task(shutdown()))
    loop.run_forever()

def sim_consensus(path: str, memory_mb: int):
  # create activated subnet
  # add subnet nodes
  subnet_id, subnet_node_count = sim_register_subnet(path, memory_mb)
  print("sim_consensus subnet_id        : ", subnet_id)
  print("sim_consensus subnet_node_count: ", subnet_node_count)

  assert subnet_id != 0, "Subnet not initialized with ID"

  # run consensus on each node
  processes = []
  for n in range(subnet_node_count):
    proc = mp.Process(target=run_consensus, args=(n, path, subnet_id), daemon=False)
    proc.start()
    processes.append(proc)

if __name__ == "__main__":
  sim_consensus(MODEL_PATH, MODEL_MEMORY_MB)