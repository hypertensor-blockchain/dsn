from typing import List, Dict
from subnet.substrate.chain_data import SubnetNode
from subnet.substrate.chain_functions import get_subnet_nodes_included, get_subnet_nodes_submittable
from substrateinterface import SubstrateInterface
from subnet.health.state_updater import ScoringProtocol
from hivemind.utils import get_logger

logger = get_logger(__name__)

# TODO: Clean this function up big time
def get_blockchain_peers_consensus_data(
  blockchain_validators: List,
  scoring_protocol: ScoringProtocol
) -> Dict:
  """
  :param blockchain_validators: List of blockchain peers
  """

  """Get peers matching blockchain model peers"""
  """If model is broken it can return `None`"""
  peers_data = scoring_protocol.run()

  """
  If model is broken then send back `model_state` as broken with a blank `peers` array
  """
  if peers_data == None:
    return {
      "model_state": "broken",
      "peers": []
    }

  """
  We first get all peers
  Then categorize by blockchain peers
  Then base the score on blockchain peers only

  Servers can be hosting blocks without being stored on the blockchain
  We only calculate `blockchain_validators` scores based on other `blockchain_validators`
  """
  model_state = "broken"
  total_blockchain_model_peers_blocks = 0
  model_num_blocks = 0
  """Initial storage for blockchain peers"""
  initial_blockchain_peers = []
  blockchain_peers = []
  for peer_result in blockchain_validators:
    blockchain_peer_id = peer_result.peer_id 
    for key, value in peers_data.items():
      if key == "model_reports":
        for data in value:
          for model_key, model_value in data.items():
            """Model State"""
            if model_key == "state":
              model_state = model_value
              if model_state == "broken":
                break

            """Model Number Of Blocks"""
            if model_key == "model_num_blocks":
              model_num_blocks = model_value

            """Model Peers"""
            if model_key == "server_rows":
              for server in model_value:
                peer_id = server['peer_id']

                """Match Hosting Peers -> Blockchain Model Peers"""
                if blockchain_peer_id == peer_id:
                  
                  span_length = server['span'].length
                  using_relay = server['using_relay']
                  total_blockchain_model_peers_blocks += span_length
                  initial_dict = {
                    "peer_id": str(peer_id),
                    "span_length": span_length,
                    "using_relay": using_relay,
                  }
                  initial_blockchain_peers.append(initial_dict)
                  break

  """If peers don't match blockchain peers, return broken"""

  if len(initial_blockchain_peers) == 0 or total_blockchain_model_peers_blocks == 0:
    return {
      "model_state": "broken",
      "peers": []
    }

  """Get scores as float"""
  peers_count = len(initial_blockchain_peers)
  scores_sum = 0
  for model_peer in initial_blockchain_peers:
    peer_num_blocks = model_peer['span_length']

    """Get temporary score based on share of blocks"""
    score = get_score(
      peer_num_blocks, 
      peers_count, 
      model_num_blocks,
      total_blockchain_model_peers_blocks
    )
    scores_sum += score
    """
      Relay servers are slower than direct servers so we lessen the score
      This ultimately incentivizes servers to be direct so we have a more efficient DHT
    """
    if model_peer['using_relay']:
      score = int(score - score * 0.33)

    dict = {
      "peer_id": str(model_peer['peer_id']),
      "score": score,
    }
    blockchain_peers.append(dict)

  """Get scores as a percentage share"""
  for model_peer in blockchain_peers:
    score = int(model_peer['score'] / scores_sum * 1e4)
    model_peer['score'] = score

  return {
    "model_state": model_state,
    "peers": blockchain_peers
  }


"""
Peers with a higher number of blocks receive higher share of rewards

       `y = k * x * x + x / max_share`       
|````````````````````````````````````````````
|                                         / `
|                                       _/  `
|                                   __/     `
y                              ___/         `
|                        ____/              `
|                 _____/                    `
|         ______/                           `
|_______/                                   `
``````````````````````x``````````````````````

This incentivizes peers to: 
  - Run less peers with higher performing GPUs
    than to run a higher count of peers with lower performing GPUs

  - *Run number of model blocks closer to other peers model blocks
    to ensure they are able to compete for rewards

*Theoretically, this will result in a tight/low deviation because
 any peers under 0.01% of the total sum of scores will not receive
 rewards, thus incentivizing them to run servers that closely resemble
 the lowest point of distribution or higher.
"""
def get_score(x: int, peers: int, blocks_per_layer: int, total_blocks: int) -> int:
  max_share_ratio = float(blocks_per_layer / total_blocks)
  k = max_share_ratio * 100
  share = float(x / total_blocks)
  # @to-do: Include throughput
  y = int((k * share * share + share) * 1e18)
  return y

def get_consensus_data(
    substrate: SubstrateInterface, 
    subnet_id: int, 
    scoring_protocol: ScoringProtocol
  ) -> Dict:
  result = get_subnet_nodes_included(
    substrate,
    subnet_id
  )

  if result is None:
    logger.warning("Included subnet nodes is None")
    return {
      "model_state": "broken",
      "peers": []
    }

  logger.info("Retrieved included subnet nodes from Hypertensor")

  subnet_nodes_data = SubnetNode.list_from_vec_u8(result["result"])

  logger.info("Retrieved subnet nodes: ", subnet_nodes_data)

  consensus_data = get_blockchain_peers_consensus_data(subnet_nodes_data, scoring_protocol)

  return consensus_data

def get_submittable_nodes(substrate: SubstrateInterface, subnet_id: int) -> List:
  result = get_subnet_nodes_submittable(
    substrate,
    subnet_id,
  )

  subnet_nodes = SubnetNode.list_from_vec_u8(result["result"])

  return subnet_nodes

def get_blochchain_model_peers_submittable(substrate: SubstrateInterface, subnet_id: int) -> Dict:
  result = get_subnet_nodes_submittable(
    substrate,
    subnet_id
  )

  subnet_nodes_data = SubnetNode.list_from_vec_u8(result["result"])

  return subnet_nodes_data

def get_eligible_consensus_block(
  epochs_interval: int, 
  initialized: int, 
  epochs: int
) -> int:
  """
  Copied from get_eligible_consensus_block ensure on blockchain in utils.rs
  """
  return initialized - (initialized % epochs_interval) + epochs_interval * epochs

def is_in_consensus_steps(
  block: int,
  epochs_interval: int, 
) -> bool:
  """
  Copied from is_in_consensus_steps utils.rs
  """
  return block % epochs_interval == 0 or (block - 1) % epochs_interval == 0

# def can_remove_or_update_model_peer(
#   block: int,
#   epochs_interval: int, 
# ) -> bool:
#   """
#   Copied from can_remove_or_update_model_peer utils.rs
#   """
#   in_consensus_steps = is_in_consensus_steps(
#     block,
#     epochs_interval, 
#   )

#   network_config = load_network_config()
#   remove_model_peer_epoch_percentage = network_config.remove_model_peer_epoch_percentage

#   block_span_can_remove_peer = int(epochs_interval * remove_model_peer_epoch_percentage)

#   start_block = 2 + (block - (block % epochs_interval))
#   end_block = block_span_can_remove_peer + (block - (block % epochs_interval))
#   return start_block <= block and block <= end_block and in_consensus_steps == False

def can_submit_consensus(
  block: int,
  epochs_interval: int, 
) -> bool:
  """
  Copied from can_submit_consensus utils.rs
  """
  in_consensus_steps = is_in_consensus_steps(
    block,
    epochs_interval, 
  )
  # can_remove_or_update_model_peer_ = can_remove_or_update_model_peer(block, epochs_interval)
  can_remove_or_update_model_peer_ = True
  return in_consensus_steps == False and can_remove_or_update_model_peer_ == False

# def get_next_eligible_submit_consensus_block(
#   epochs_interval: int, 
#   last_block: int
# ) -> int:
#   """Returns next eligible block based on last time user submitted"""
#   return epochs_interval + (last_block - (last_block % epochs_interval))

def get_next_eligible_submit_consensus_block(
  epochs_interval: int, 
  last_block: int
) -> int:
  """Returns next eligible block based on last time user submitted"""

  # network_config = load_network_config()
  # remove_model_peer_epoch_percentage = network_config.remove_model_peer_epoch_percentage

  # block_span_can_remove_peer = int(epochs_interval * remove_model_peer_epoch_percentage)

  return epochs_interval + (last_block - (last_block % epochs_interval))

def get_next_epoch_start_block(
  epochs_length: int, 
  block: int
) -> int:
  """Returns next start block for next epoch"""
  return epochs_length + (block - (block % epochs_length))

def safe_div(n, d):
  return n / d if d else 0
