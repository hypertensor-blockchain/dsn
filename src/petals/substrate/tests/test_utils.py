import dataclasses
import os
import time
from typing import Optional
from substrateinterface import SubstrateInterface, Keypair
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import asdict, is_dataclass
import threading

from hivemind.utils import get_logger

from petals.substrate.chain_data import RewardsData, SubnetNode
from petals.substrate.chain_functions import activate_subnet, add_subnet_node, attest, get_epoch_length, get_rewards_submission, get_rewards_validator, get_subnet_data, get_subnet_id_by_path, get_subnet_nodes_included, validate
from petals.substrate.config import SubstrateConfigCustom
from petals.substrate.utils import get_submittable_nodes

logger = get_logger(__name__)

load_dotenv(os.path.join(Path.cwd(), '.env'))
LOCAL_URL = os.getenv('LOCAL_RPC')
DEV_URL = os.getenv('DEV_RPC')

# s per block
BLOCK_SECS = 6

MODEL_PATH = "bigscience/bloom-560m"
MODEL_MEMORY_MB = 50000

PEER_IDS = [
  "QmedTaZXmULqwspJXz44SsPZyTNKxhnnFvYRajfH7MGhCY",
  "QmQGTqmM7NKjV6ggU1ZCap8zWiyKR89RViDXiqehSiCpY5",
  "12D3KooWBxMLje7yExEBhZQqbuVL1giKPpN8DieYkL3Wz7sTku7T",
  "12D3KooWEDYmpQVW6ixD7MijciZcZMuPtdrvNbeC4Jr1cxV1hJZe",
  "12D3KooWJAAqbBW3YXJE42TAGgXTRVxZwmWuqY9yBneLfsDFiA8b",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8YN",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8YL",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8YP",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8YQ",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8Y1",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8Y2",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8Y3",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8Y4",
  "12D3KooWGB94YYemuff4AucWo8RfV5mzHWLZc5HvhWqBXrk2W8Y5",
] 

@dataclasses.dataclass
class SubstrateConfig:
  interface: SubstrateInterface
  keypair: Keypair
  account_id: str

def get_substrate_config(n: int):
  return SubstrateConfig(
    SubstrateInterface(url=LOCAL_URL),
    Keypair.create_from_uri(f"//{str(n)}"),
    Keypair.create_from_uri(f"//{str(n)}").ss58_address
  )

# @dataclasses.dataclass
# class SubnetNode:
#   account_id: str
#   peer_id: str

def get_subnet_nodes_consensus_data(count: int):
  subnet_nodes = []
  for i in range(count):
    node = {
      'peer_id': PEER_IDS[i],
      'score': 10000
    }
    subnet_nodes.append(node)
    
  return subnet_nodes


class TestConsensus(threading.Thread):
  """
  Houses logic for validating and attesting consensus data per epochs for rewards

  This can be ran before or during a model activation.

  If before, it will wait until the subnet is successfully voted in, if the proposal to initialize the subnet fails,
  it will not stop running.

  If after, it will begin to validate and or attest epochs
  """
  def __init__(self, path: str, account_id: str, substrate: SubstrateConfigCustom):
    super().__init__()
    self.subnet_id = None # Not required in case of not initialized yet
    self.path = path
    self.account_id = account_id
    self.subnet_accepting_consensus = False
    self.subnet_node_eligible = False
    self.subnet_initialized = 9223372036854775807 # max int
    self.last_validated_or_attested_epoch = 0

    # self.substrate_config = SubstrateConfigCustom(phrase, url)
    self.substrate_config = substrate

    # blockchain constants
    self.epoch_length = int(str(get_epoch_length(self.substrate_config.interface)))

  def run(self):
    while True:
      try:
        block_hash = self.substrate_config.interface.get_block_hash()
        block_number = self.substrate_config.interface.get_block_number(block_hash)

        epoch = int(block_number / self.epoch_length)
        logger.info("Epoch: %s " % epoch)

        logger.info("Last Validated Epoch: %s " % self.last_validated_or_attested_epoch)

        # skip if already validated or attested epoch
        if epoch <= self.last_validated_or_attested_epoch:
          logger.info("Already completed epoch: %s, waiting for the next " % epoch)
          time.sleep(BLOCK_SECS)
          continue

        next_epoch_start_block = self.epoch_length + (block_number - (block_number % self.epoch_length))
        
        # Ensure subnet is activated
        # this will iterate until the subnet is activated
        if self.subnet_accepting_consensus == False:
          activated = self._activate_subnet()
          if activated == True:
            continue
          else:
            # Sleep until voting is complete
            time.sleep(BLOCK_SECS)
            continue
        """
        Is subnet node initialized and eligible to submit consensus
        """
        # subnet is eligible to accept consensus
        # check if we are submittable
        # in order to be submittable:
        # - Must stake onchain
        # - Must be Submittable subnet node class
        if self.subnet_node_eligible == False:
          # submittable_nodes = get_subnet_nodes_submittable(
          #   self.substrate_config.interface,
          #   self.subnet_id,
          # )
          print("self.account_id: \n", self.account_id)
          submittable_nodes = get_submittable_nodes(
            self.substrate_config.interface,
            self.subnet_id,
          )
          print("submittable_nodes: \n", submittable_nodes)

          for node_set in submittable_nodes:
            if node_set.account_id == self.account_id:
              self.subnet_node_eligible = True
              break
          
          if self.subnet_node_eligible == False:
            logger.info("Node not eligible for consensus, sleeping until next epoch")
            time.sleep(BLOCK_SECS)
            continue

        # is epoch submitted yet

        # is validator?
        validator = self._get_validator(epoch)
        print("\n Validator is :", validator)

        if validator == None:
          logger.info("Validator not chosen for epoch %s yet, checking next block" % epoch)
          time.sleep(BLOCK_SECS)
          continue
        else:
          logger.info("Validator for epoch %s is %s" % (epoch, validator))

        is_validator = validator == self.account_id
        if is_validator:
          logger.info("We're the chosen validator for epoch %s, validating and auto-attesting..." % epoch)
          # check if validated 
          validated = False
          if validated is False:
            self.validate()
            self.last_validated_or_attested_epoch = epoch

          # continue to next epoch, no need to attest
          time.sleep(BLOCK_SECS)
          continue

        # we are not validator, we must attest or not attest
        # wait until validated by epochs chosen validator

        # get epoch before waiting for validator to validate to ensure we don't get stuck 
        initial_epoch = epoch
        attestation_complete = False
        logger.info("Starting attestation check")
        while True:
          # wait for validator on every block
          time.sleep(BLOCK_SECS)
          block_hash = self.substrate_config.interface.get_block_hash()
          block_number = self.substrate_config.interface.get_block_number(block_hash)

          epoch = int(block_number / self.epoch_length)
          logger.info("Epoch in Attestation: %s " % epoch)

          # If we made it to the next epoch, break
          # This likely means the chosen validator never submitted consensus data
          if epoch > initial_epoch:
            logger.info("Validator didn't submit consensus data, moving to the next epoch: %s" % epoch)
            break

          result = self.attest(epoch)
          if result == None:
            # If None, still waiting for validator to submit data
            continue
          else:
            # successful attestation, break and go to next epoch
            self.last_validated_or_attested_epoch = epoch
            break
      except Exception as e:
        logger.error("TestConsensus Error: %s" % e, exc_info=True)

  def validate(self):
    print("validate")
    """Get rewards data and submit consensus"""
    consensus_data = self._get_consensus_data()
    self._do_validate(consensus_data)

  def attest(self, epoch: int):
    print("attest")
    """Get rewards data from another validator and attest that data if valid"""
    validator_consensus_submission = self._get_validator_consensus_submission(epoch)

    if validator_consensus_submission == None:
      logger.info("Waiting for validator to submit")
      return None

    # backup check if validator node restarts in the middle of an epoch to ensure they don't tx again
    if self._has_attested(validator_consensus_submission["attests"]):
      logger.info("Has attested already")
      return None

    validator_consensus_data = RewardsData.list_from_scale_info(validator_consensus_submission["data"])

    logger.info("Checking if we should attest the validators submission")
    logger.info("Generating consensus data")
    consensus_data = self._get_consensus_data()
    should_attest = self.should_attest(validator_consensus_data, consensus_data)
    logger.info("Should attest is: %s", should_attest)

    if should_attest:
      logger.info("Validators data is confirmed valid, attesting data...")
      return self._do_attest()
    else:
      logger.info("Validators data is not valid, skipping attestation.")
      return None

    # valid = True

    # logger.info("Checking if we should attest the validators submission")


    # """
    # """
    # # Simply validate to ensure mechanism compatibility

    # logger.info("Generating consensus data")
    # consensus_data = self._get_consensus_data()
    # should_attest = self.should_attest(validator_consensus_data, consensus_data)
    # logger.info("Should attest is: %s", should_attest)

    # if valid:
    #   logger.info("Validators data is confirmed valid, attesting data...")
    #   return self._do_attest()
    # else:
    #   logger.info("Validators data is not valid, skipping attestation.")
    #   return None
    
  def _do_validate(self, data):
    print("_do_validate")
    try:
      receipt = validate(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        self.subnet_id,
        data
      )
      return receipt
    except Exception as e:
      logger.error("Validation Error: %s" % e)
      return None
    
  def _do_attest(self):
    print("_do_attest")
    try:
      receipt = attest(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        self.subnet_id,
      )
      return receipt
    except Exception as e:
      logger.error("Attestation Error: %s" % e)
      return None

  def _get_consensus_data(self):
    print("_get_consensus_data")
    """"""
    # consensus_data = get_subnet_nodes_consensus_data(len(PEER_IDS))
    
    # imitates what consensus.py does

    # get nodes on chain that are supposed to be included in consensus
    result = get_subnet_nodes_included(
      self.substrate_config.interface,
      self.subnet_id
    )
    print("_get_consensus_data result", result)

    subnet_nodes_data = SubnetNode.list_from_vec_u8(result["result"])
    print("_get_consensus_data subnet_nodes_data", subnet_nodes_data)

    # check test PEER_IDS versus 
    # filter PEER_IDS that don't match onchain subnet nodes
    peer_set = set(PEER_IDS)
    print("_get_consensus_data peer_set", peer_set)
    filtered_list = [d.peer_id for d in subnet_nodes_data if d.peer_id in peer_set]

    print("filtered_list", filtered_list)

    consensus_data = []
    for peer_id in filtered_list:
      node = {
        'peer_id': peer_id,
        'score': 10000
      }
      consensus_data.append(node)


    print("consensus_data", consensus_data)
    return consensus_data

  def _get_validator_consensus_submission(self, epoch: int):
    print("_get_validator_consensus_submission")
    """Get and return the consensus data from the current validator"""
    rewards_submission = get_rewards_submission(
      self.substrate_config.interface,
      self.subnet_id,
      epoch
    )
    return rewards_submission

  def _has_attested(self, attested_account_ids) -> bool:
    """Get and return the consensus data from the current validator"""
    for account_id in attested_account_ids:
      if account_id == self.account_id:
        return True
    return False

  def _get_validator(self, epoch):
    print("_get_validator")
    validator = get_rewards_validator(
      self.substrate_config.interface,
      self.subnet_id,
      epoch
    )
    return validator
  
  def _activate_subnet(self):
    print("_activate_subnet")
    """
    Attempt to activate subnet

    Will wait for subnet to be activated

    1. Check if subnet activated
    2. If not activated, calculate turn to activate based on peer index
    3. Wait for the turn to activate to pass

    Returns:
      bool: True if subnet was successfully activated, False otherwise.
    """
    subnet_id = get_subnet_id_by_path(self.substrate_config.interface, self.path)
    print("_activate_subnet subnet_id", subnet_id)
    assert subnet_id is not None, logger.error("Cannot find subnet at path: %s", self.path)
    
    subnet_data = get_subnet_data(
      self.substrate_config.interface,
      subnet_id
    )
    print("_activate_subnet subnet_data", subnet_data)
    assert subnet_data is not None, logger.error("Cannot find subnet at ID: %s", subnet_id)

    initialized = int(str(subnet_data['initialized']))
    registration_blocks = int(str(subnet_data['registration_blocks']))
    activation_block = initialized + registration_blocks

    # if we didn't activate the node, someone indexed before us should have - see logic below
    if subnet_data['activated'] > 0:
      logger.info("Subnet activated, just getting things set up for consensus...")
      self.subnet_accepting_consensus = True
      self.subnet_id = int(str(subnet_id))
      self.subnet_activated = int(str(subnet_data["activated"]))
      return True

    # randomize activating subnet by node entry index
    # when subnet is in registration, all new subnet nodes are ``Submittable`` classification
    # so we check all submittable nodes
    submittable_nodes = get_submittable_nodes(
      self.substrate_config.interface,
      int(str(subnet_id)),
    )
    print("_activate_subnet submittable_nodes", submittable_nodes)

    n = 0
    for node_set in submittable_nodes:
      n+=1
      if node_set.account_id == self.account_id:
        break

    print("_activate_subnet n", n)

    min_node_activation_block = activation_block + BLOCK_SECS*10 * (n-1)
    max_node_activation_block = activation_block + BLOCK_SECS*10 * n
    print("_activate_subnet min_node_activation_block", min_node_activation_block)
    print("_activate_subnet max_node_activation_block", max_node_activation_block)

    block_hash = self.substrate_config.interface.get_block_hash()
    block_number = self.substrate_config.interface.get_block_number(block_hash)
    print("_activate_subnet block_number", block_number)

    if block_number < min_node_activation_block or block_number >= max_node_activation_block:
      # delta = min_node_activation_block - block_number
      # logger.info(f"Waiting until activation block for {delta} blocks")
      time.sleep(BLOCK_SECS)
      self._activate_subnet()

    # Redunant, but if we missed our turn to activate, wait until someone else has to start consensus
    if block_number >= max_node_activation_block:
      time.sleep(BLOCK_SECS)
      self._activate_subnet()

    # if within our designated activation block, then activate
    # activation is a no-weight transaction, meaning it costs nothing to do
    if block_number >= min_node_activation_block and block_number < max_node_activation_block:
      print("_activate_subnet node activating subnet")

      # check if activated already by another node
      subnet_data = get_subnet_data(
        self.substrate_config.interface,
        int(str(subnet_id))
      )
      print("_activate_subnet subnet_data", subnet_data)

      if subnet_data['activated'] > 0:
        print("_activate_subnet already activated")
        self.subnet_accepting_consensus = True
        self.subnet_id = int(str(subnet_id))
        self.subnet_activated = True
        return True

      print("_activate_subnet attempting to activate subnet", n)
      # Attempt to activate subnet
      receipt = activate_subnet(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        int(str(subnet_id)),
      )
      print("_activate_subnet is_success", receipt.is_success)
      for event in receipt.triggered_events:
        print(f'* {event.value}')
        
      if receipt.is_success:
        self.subnet_accepting_consensus = True
        self.subnet_id = int(str(subnet_id))
        self.subnet_activated = True
        return True

    # check if subnet failed to be activated
    # this means:
    # someone else activated it and code miscalculated (contact devs with error if so)
    # or the subnet didn't meet its activation requirements and should revert on the next ``_activate_subnet`` call
    time.sleep(BLOCK_SECS)
    self._activate_subnet()

  def should_attest(self, validator_data, my_data):
    print("should_attest")
    print("should_attest validator_data", validator_data)
    print("should_attest validator_data len", len(validator_data))
    print("should_attest my_data", my_data)
    print("should_attest my_data len", len(my_data))
    """Checks if two arrays of dictionaries match, regardless of order."""

    # if data length differs and validator did upload data, return False
    # this means the validator thinks the subnet is broken, but we do not
    if len(validator_data) != len(my_data) and len(validator_data) > 0:
      return False

    # if validator submitted no data, and we have also found the subnet is broken
    if len(validator_data) == len(my_data) and len(validator_data) == 0:
      return True
    
    # otherwise, check the data matches
    # at this point, the
    
    # use ``asdict`` because data is decoded from blockchain as dataclass
    # we assume the lists are consistent across all elements
    # Convert validator_data to a set
    set1 = set(frozenset(asdict(d).items()) for d in validator_data)

    # Convert my_data to a set
    set2 = set(frozenset(d.items()) for d in my_data)

    intersection = set1.intersection(set2)
    logger.info("Matching intersection of %s validator data" % ((len(intersection))/len(set1) * 100))
    logger.info("Validator matching intersection of %s my data" % ((len(intersection))/len(set2) * 100))

    return set1 == set2

  # def should_attest(self, validator_data, my_data):
  #   """Checks if two arrays of dictionaries match, regardless of order."""

  #   # if data length differs and validator did upload data, return False
  #   # this means the validator thinks the subnet is broken, but we do not
  #   if len(validator_data) != len(my_data) and len(validator_data) > 0:
  #     return False

  #   # if validator submitted no data, and we have also found the subnet is broken
  #   if len(validator_data) == len(my_data) and len(validator_data) == 0:
  #     return True
    
  #   # otherwise, check the data matches
  #   # at this point, the
    
  #   # use ``asdict`` because data is decoded from blockchain as dataclass
  #   # we assume the lists are consistent across all elements
  #   if is_dataclass(validator_data[0]):
  #     print("should_attest validator_data is_dataclass")
  #     set1 = set(frozenset(asdict(d).items()) for d in validator_data)
  #   else:
  #     print("should_attest validator_data else")
  #     set1 = set(frozenset(d.items()) for d in validator_data)

  #   if is_dataclass(my_data[0]):
  #     print("should_attest my_data is_dataclass")
  #     set2 = set(frozenset(asdict(d).items()) for d in my_data)
  #   else:
  #     print("should_attest my_data else")
  #     set2 = set(frozenset(d.items()) for d in my_data)

  #   intersection = set1.intersection(set2)
  #   logger.info("Matching intersection of %s validator data" % ((len(intersection))/len(set1) * 100))
  #   logger.info("Validator matching intersection of %s my data" % ((len(intersection))/len(set2) * 100))

  #   return set1 == set2

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
  add_subnet_node(substrate_config.interface, substrate_config.keypair, subnet_id, PEER_IDS[idx], 1000e18)

