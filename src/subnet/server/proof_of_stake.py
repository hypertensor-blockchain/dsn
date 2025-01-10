import os
import threading
from venv import logger

from subnet.substrate.chain_data import SubnetNode
from subnet.substrate.chain_functions import is_subnet_node_by_peer_id
from subnet.substrate.config import BLOCK_SECS, SubstrateConfig
from subnet.substrate.consensus import Consensus
from subnet.substrate.utils import get_next_epoch_start_block

from hivemind import DHT, get_dht_time, RoutingTable
from hivemind.dht.routing import RoutingTable

from subnet.utils.repeated_timer import RepeatedTimer

class ProofOfStake(threading.Thread):
    """
    Runs Proof of Stake mechanism, periodically checks that each peer in the routing pool is staked,
    preferably at least once per epoch. If a peer is not staked, they are removed
    """

    def __init__(
      self,
      converted_model_name_or_path: str,
      dht: DHT,
      consensus: Consensus,
      routing_table: RoutingTable,
    ): 
      super().__init__(daemon=True)
      self.subnet_id = None
      self.converted_model_name_or_path = converted_model_name_or_path
      self.dht = dht
      self.routing_table = routing_table
      self.consensus = consensus
      
    def run(self):
      """
      Listens for proposals while running inference validation PoI
      Only one should be running at a time.
      When a proposal is found, shut down the inference validator and validate the proposal data
      """
      t1 = threading.Thread(target=RepeatedTimer(15, self.run_pos_in_background), args=())
      t1.start()
      t1.join()

    def run_pos_in_background(self):
      # wait until subnet is initialized
      if self.consensus.self.subnet_id is None:
        return
      
      try:
        logger.info("Running POS mechanism")
        rpc = os.getenv('LOCAL_RPC')
        if rpc is None:
          return

        node_update_time = os.getenv('POS_INTERVAL')
        if node_update_time is None:
          return
        
        dht_time = get_dht_time()

        for peer_id, last_updated in self.routing_table.peer_id_to_last_updated:
          # check nodes on an interval basis
          # newly entered peers get a grace period before being checked for having a proof of stake
          if dht_time - last_updated > node_update_time:
            # get on-chain staking data from ``peer_id`` to qualify if staked
            # we only check if they are a subnet node because they must be staked to be included
            is_staked = is_subnet_node_by_peer_id(
              SubstrateConfig.interface,
              self.subnet_id,
              peer_id
            )
            if is_staked:
              self.routing_table.peer_id_to_last_updated[peer_id] = dht_time
            else:
              node_id = self.routing_table.uid_to_peer_id.get(node_id, None)
              if node_id is not None:
                logger.info("Removing peer %s from routing table", peer_id)
                self.__delitem__(node_id)
      except Exception as e:
          logger.error(f"Error running POS mechanism: {e}", exc_info=True)
