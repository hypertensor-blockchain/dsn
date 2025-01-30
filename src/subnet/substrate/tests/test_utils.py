import dataclasses
import os
import time
from typing import List, Optional, Tuple
from substrateinterface import SubstrateInterface, Keypair
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import asdict, is_dataclass
import threading

from hivemind.proto import crypto_pb2
from hivemind.utils import get_logger
from hivemind.utils.auth import POSAuthorizerLive
from subnet.substrate.chain_data import RewardsData, SubnetNode
from subnet.substrate.chain_functions import activate_subnet, add_subnet_node, attest, get_block_number, get_epoch_length, get_rewards_submission, get_rewards_validator, get_subnet_data, get_subnet_id_by_path, get_subnet_nodes_included, validate
from subnet.substrate.config import SubstrateConfigCustom
from subnet.substrate.consensus import AttestReason
from subnet.substrate.utils import get_next_epoch_start_block, get_submittable_nodes, safe_div
from hivemind.utils.crypto import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from hivemind import PeerID

logger = get_logger(__name__)

load_dotenv(os.path.join(Path.cwd(), '.env'))
LOCAL_URL = os.getenv('LOCAL_RPC')
DEV_URL = os.getenv('DEV_RPC')

# s per block
BLOCK_SECS = 6

MODEL_PATH = "bigscience/bloom-560m"
MODEL_MEMORY_MB = 2000

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
class SubnetNodesData:
  peer_id: str
  private_key: Ed25519PrivateKey
  authorizer: POSAuthorizerLive

def generate_subnet_nodes(count: int):
  subnet_nodes_data: List[SubnetNodesData] = []

  for n in range(count):
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_key = Ed25519PrivateKey(private_key=private_key)

    public_key = private_key.public_key().public_bytes(
      encoding=serialization.Encoding.Raw,
      format=serialization.PublicFormat.Raw,
    )

    encoded_public_key = crypto_pb2.PublicKey(
      key_type=crypto_pb2.Ed25519,
      data=public_key,
    ).SerializeToString()

    encoded_digest = b"\x00$" + encoded_public_key

    peer_id = PeerID(encoded_digest)

@dataclasses.dataclass
class SubstrateConfigTest:
  interface: SubstrateInterface
  keypair: Keypair
  account_id: str

def get_substrate_config(n: int):
  return SubstrateConfigTest(
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


# class TestConsensus(threading.Thread):
#   """
#   Houses logic for validating and attesting consensus data per epochs for rewards

#   This can be ran before or during a model activation.

#   If before, it will wait until the subnet is successfully voted in, if the proposal to initialize the subnet fails,
#   it will not stop running.

#   If after, it will begin to validate and or attest epochs
#   """
#   def __init__(self, path: str, substrate: SubstrateConfigCustom):
#     super().__init__()
#     self.subnet_id = None # Not required in case of not initialized yet
#     self.path = path
#     self.subnet_accepting_consensus = False
#     self.subnet_node_eligible = False
#     self.subnet_initialized = 9223372036854775807 # max int
#     self.last_validated_or_attested_epoch = 0

#     # self.substrate_config = SubstrateConfigCustom(phrase, url)
#     self.substrate_config = substrate
#     self.account_id = substrate.account_id
#     print("TestConsensus __init__ account_id", self.account_id)

#     # blockchain constants
#     self.epoch_length = int(str(get_epoch_length(self.substrate_config.interface)))

#   def run(self):
#     while True:
#       try:
#         block_hash = self.substrate_config.interface.get_block_hash()
#         block_number = self.substrate_config.interface.get_block_number(block_hash)

#         epoch = int(block_number / self.epoch_length)
#         logger.info("Epoch: %s " % epoch)

#         logger.info("Last Validated Epoch: %s " % self.last_validated_or_attested_epoch)

#         # skip if already validated or attested epoch
#         if epoch <= self.last_validated_or_attested_epoch and self.subnet_accepting_consensus:
#           logger.info("Already completed epoch: %s, waiting for the next " % epoch)
#           time.sleep(BLOCK_SECS)
#           continue

#         next_epoch_start_block = self.epoch_length + (block_number - (block_number % self.epoch_length))
        
#         # Ensure subnet is activated
#         # this will iterate until the subnet is activated
#         if self.subnet_accepting_consensus == False:
#           activated = self._activate_subnet()
#           if activated == True:
#             continue
#           else:
#             # Sleep until voting is complete
#             time.sleep(BLOCK_SECS)
#             continue
#         """
#         Is subnet node initialized and eligible to submit consensus
#         """
#         # subnet is eligible to accept consensus
#         # check if we are submittable
#         # in order to be submittable:
#         # - Must stake onchain
#         # - Must be Submittable subnet node class
#         if self.subnet_node_eligible == False:
#           submittable_nodes = get_submittable_nodes(
#             self.substrate_config.interface,
#             self.subnet_id,
#           )

#           for node_set in submittable_nodes:
#             if node_set.account_id == self.account_id:
#               self.subnet_node_eligible = True
#               break
          
#           if self.subnet_node_eligible == False:
#             logger.info("Node not eligible for consensus, sleeping until next epoch")
#             time.sleep(BLOCK_SECS)
#             continue

#         # is epoch submitted yet

#         # is validator?
#         validator = self._get_validator(epoch)
#         print("\n Validator is :", validator)

#         if validator == None:
#           logger.info("Validator not chosen for epoch %s yet, checking next block" % epoch)
#           time.sleep(BLOCK_SECS)
#           continue
#         else:
#           logger.info("Validator for epoch %s is %s" % (epoch, validator))

#         is_validator = validator == self.account_id
#         if is_validator:
#           logger.info("We're the chosen validator for epoch %s, validating and auto-attesting..." % epoch)
#           # check if validated 
#           validated = False
#           if validated is False:
#             self.validate()
#             self.last_validated_or_attested_epoch = epoch

#           # continue to next epoch, no need to attest
#           time.sleep(BLOCK_SECS)
#           continue

#         # we are not validator, we must attest or not attest
#         # wait until validated by epochs chosen validator

#         # get epoch before waiting for validator to validate to ensure we don't get stuck 
#         initial_epoch = epoch
#         attestation_complete = False
#         logger.info("Starting attestation check")
#         while True:
#           # wait for validator on every block
#           time.sleep(BLOCK_SECS)
#           block_hash = self.substrate_config.interface.get_block_hash()
#           block_number = self.substrate_config.interface.get_block_number(block_hash)

#           epoch = int(block_number / self.epoch_length)
#           logger.info("Epoch in Attestation: %s " % epoch)

#           # If we made it to the next epoch, break
#           # This likely means the chosen validator never submitted consensus data
#           if epoch > initial_epoch:
#             logger.info("Validator didn't submit consensus data, moving to the next epoch: %s" % epoch)
#             break

#           result = self.attest(epoch)
#           if result == None:
#             # If None, still waiting for validator to submit data
#             continue
#           else:
#             # successful attestation, break and go to next epoch
#             self.last_validated_or_attested_epoch = epoch
#             break
#       except Exception as e:
#         logger.error("TestConsensus Error: %s" % e, exc_info=True)

#   def validate(self):
#     print("validate")
#     """Get rewards data and submit consensus"""
#     consensus_data = self._get_consensus_data()
#     self._do_validate(consensus_data)

#   def attest(self, epoch: int):
#     print("attest")
#     """Get rewards data from another validator and attest that data if valid"""
#     validator_consensus_submission = self._get_validator_consensus_submission(epoch)

#     if validator_consensus_submission == None:
#       logger.info("Waiting for validator to submit")
#       return None

#     # backup check if validator node restarts in the middle of an epoch to ensure they don't tx again
#     if self._has_attested(validator_consensus_submission["attests"]):
#       logger.info("Has attested already")
#       return None

#     validator_consensus_data = RewardsData.list_from_scale_info(validator_consensus_submission["data"])

#     logger.info("Checking if we should attest the validators submission")
#     logger.info("Generating consensus data")
#     consensus_data = self._get_consensus_data()
#     should_attest = self.should_attest(validator_consensus_data, consensus_data)
#     logger.info("Should attest is: %s", should_attest)

#     if should_attest:
#       logger.info("Validators data is confirmed valid, attesting data...")
#       return self._do_attest()
#     else:
#       logger.info("Validators data is not valid, skipping attestation.")
#       return None

#     # valid = True

#     # logger.info("Checking if we should attest the validators submission")


#     # """
#     # """
#     # # Simply validate to ensure mechanism compatibility

#     # logger.info("Generating consensus data")
#     # consensus_data = self._get_consensus_data()
#     # should_attest = self.should_attest(validator_consensus_data, consensus_data)
#     # logger.info("Should attest is: %s", should_attest)

#     # if valid:
#     #   logger.info("Validators data is confirmed valid, attesting data...")
#     #   return self._do_attest()
#     # else:
#     #   logger.info("Validators data is not valid, skipping attestation.")
#     #   return None
    
#   def _do_validate(self, data):
#     print("_do_validate")
#     try:
#       receipt = validate(
#         self.substrate_config.interface,
#         self.substrate_config.keypair,
#         self.subnet_id,
#         data
#       )
#       return receipt
#     except Exception as e:
#       logger.error("Validation Error: %s" % e)
#       return None
    
#   def _do_attest(self):
#     print("_do_attest")
#     try:
#       receipt = attest(
#         self.substrate_config.interface,
#         self.substrate_config.keypair,
#         self.subnet_id,
#       )
#       return receipt
#     except Exception as e:
#       logger.error("Attestation Error: %s" % e)
#       return None

#   def _get_consensus_data(self):
#     print("_get_consensus_data")
#     """"""
#     # consensus_data = get_subnet_nodes_consensus_data(len(PEER_IDS))
    
#     # imitates what consensus.py does

#     # get nodes on chain that are supposed to be included in consensus
#     result = get_subnet_nodes_included(
#       self.substrate_config.interface,
#       self.subnet_id
#     )
#     print("_get_consensus_data result", result)

#     subnet_nodes_data = SubnetNode.list_from_vec_u8(result["result"])
#     print("_get_consensus_data subnet_nodes_data", subnet_nodes_data)

#     # check test PEER_IDS versus 
#     # filter PEER_IDS that don't match onchain subnet nodes
#     peer_set = set(PEER_IDS)
#     print("_get_consensus_data peer_set", peer_set)
#     filtered_list = [d.peer_id for d in subnet_nodes_data if d.peer_id in peer_set]

#     print("filtered_list", filtered_list)

#     consensus_data = []
#     for peer_id in filtered_list:
#       node = {
#         'peer_id': peer_id,
#         'score': 10000
#       }
#       consensus_data.append(node)


#     print("consensus_data", consensus_data)
#     return consensus_data

#   def _get_validator_consensus_submission(self, epoch: int):
#     print("_get_validator_consensus_submission")
#     """Get and return the consensus data from the current validator"""
#     rewards_submission = get_rewards_submission(
#       self.substrate_config.interface,
#       self.subnet_id,
#       epoch
#     )
#     return rewards_submission

#   def _has_attested(self, attested_account_ids) -> bool:
#     """Get and return the consensus data from the current validator"""
#     for account_id in attested_account_ids:
#       if account_id == self.account_id:
#         return True
#     return False

#   def _get_validator(self, epoch):
#     print("_get_validator")
#     validator = get_rewards_validator(
#       self.substrate_config.interface,
#       self.subnet_id,
#       epoch
#     )
#     return validator
  
#   def _activate_subnet(self):
#     print("_activate_subnet")
#     """
#     Attempt to activate subnet

#     Will wait for subnet to be activated

#     1. Check if subnet activated
#     2. If not activated, calculate turn to activate based on peer index
#     3. Wait for the turn to activate to pass

#     Returns:
#       bool: True if subnet was successfully activated, False otherwise.
#     """
#     print("_activate_subnet path", self.path)
#     subnet_id = get_subnet_id_by_path(self.substrate_config.interface, self.path)
#     print("_activate_subnet subnet_id", subnet_id)
#     assert subnet_id is not None or subnet_id is not 'None', logger.error("Cannot find subnet at path: %s", self.path)
    
#     subnet_data = get_subnet_data(
#       self.substrate_config.interface,
#       subnet_id
#     )
#     print("_activate_subnet subnet_data", subnet_data)
#     assert subnet_data is not None or subnet_data is not 'None', logger.error("Cannot find subnet at ID: %s", subnet_id)

#     initialized = int(str(subnet_data['initialized']))
#     registration_blocks = int(str(subnet_data['registration_blocks']))
#     activation_block = initialized + registration_blocks

#     print("_activate_subnet initialized", initialized)
#     print("_activate_subnet activation_block", activation_block)

#     # if we didn't activate the node, someone indexed before us should have - see logic below
#     if subnet_data['activated'] > 0:
#       logger.info("Subnet activated, just getting set up for consensus...")
#       self.subnet_accepting_consensus = True
#       self.subnet_id = int(str(subnet_id))
#       self.subnet_activated = int(str(subnet_data["activated"]))
#       return True

#     # randomize activating subnet by node entry index
#     # when subnet is in registration, all new subnet nodes are ``Submittable`` classification
#     # so we check all submittable nodes
#     submittable_nodes = get_submittable_nodes(
#       self.substrate_config.interface,
#       int(str(subnet_id)),
#     )
#     print("_activate_subnet submittable_nodes", submittable_nodes)

#     n = 0
#     for node_set in submittable_nodes:
#       n+=1
#       if node_set.account_id == self.account_id:
#         break

#     print("_activate_subnet n", n)

#     min_node_activation_block = activation_block + BLOCK_SECS*10 * (n-1)
#     max_node_activation_block = activation_block + BLOCK_SECS*10 * n
#     print("_activate_subnet min_node_activation_block", min_node_activation_block)
#     print("_activate_subnet max_node_activation_block", max_node_activation_block)

#     block_hash = self.substrate_config.interface.get_block_hash()
#     block_number = self.substrate_config.interface.get_block_number(block_hash)
#     print("_activate_subnet block_number", block_number)

#     if block_number < min_node_activation_block or block_number >= max_node_activation_block:
#       # delta = min_node_activation_block - block_number
#       # logger.info(f"Waiting until activation block for {delta} blocks")
#       time.sleep(BLOCK_SECS)
#       self._activate_subnet()

#     # Redunant, but if we missed our turn to activate, wait until someone else has to start consensus
#     if block_number >= max_node_activation_block:
#       time.sleep(BLOCK_SECS)
#       self._activate_subnet()

#     # if within our designated activation block, then activate
#     # activation is a no-weight transaction, meaning it costs nothing to do
#     if block_number >= min_node_activation_block and block_number < max_node_activation_block:
#       print("_activate_subnet node activating subnet")

#       # check if activated already by another node
#       subnet_data = get_subnet_data(
#         self.substrate_config.interface,
#         int(str(subnet_id))
#       )
#       print("_activate_subnet subnet_data", subnet_data)

#       if subnet_data['activated'] > 0:
#         print("_activate_subnet already activated")
#         self.subnet_accepting_consensus = True
#         self.subnet_id = int(str(subnet_id))
#         self.subnet_activated = True
#         return True

#       print("_activate_subnet attempting to activate subnet", n)
#       # Attempt to activate subnet
#       receipt = activate_subnet(
#         self.substrate_config.interface,
#         self.substrate_config.keypair,
#         int(str(subnet_id)),
#       )
#       print("_activate_subnet is_success", receipt.is_success)
#       for event in receipt.triggered_events:
#         print(f'* {event.value}')
        
#       if receipt.is_success:
#         self.subnet_accepting_consensus = True
#         self.subnet_id = int(str(subnet_id))
#         self.subnet_activated = True
#         return True

#     # check if subnet failed to be activated
#     # this means:
#     # someone else activated it and code miscalculated (contact devs with error if so)
#     # or the subnet didn't meet its activation requirements and should revert on the next ``_activate_subnet`` call
#     # time.sleep(BLOCK_SECS)
#     # self._activate_subnet()

#     return False

#   def should_attest(self, validator_data, my_data):
#     print("should_attest")
#     print("should_attest validator_data", validator_data)
#     print("should_attest validator_data len", len(validator_data))
#     print("should_attest my_data", my_data)
#     print("should_attest my_data len", len(my_data))
#     """Checks if two arrays of dictionaries match, regardless of order."""

#     # if data length differs and validator did upload data, return False
#     # this means the validator thinks the subnet is broken, but we do not
#     if len(validator_data) != len(my_data) and len(validator_data) > 0:
#       return False

#     # if validator submitted no data, and we have also found the subnet is broken
#     if len(validator_data) == len(my_data) and len(validator_data) == 0:
#       return True
    
#     # otherwise, check the data matches
#     # at this point, the
    
#     # use ``asdict`` because data is decoded from blockchain as dataclass
#     # we assume the lists are consistent across all elements
#     # Convert validator_data to a set
#     set1 = set(frozenset(asdict(d).items()) for d in validator_data)

#     # Convert my_data to a set
#     set2 = set(frozenset(d.items()) for d in my_data)

#     intersection = set1.intersection(set2)
#     logger.info("Matching intersection of %s validator data" % ((len(intersection))/len(set1) * 100))
#     logger.info("Validator matching intersection of %s my data" % ((len(intersection))/len(set2) * 100))

#     return set1 == set2

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



class Consensus(threading.Thread):
  """
  Houses logic for validating and attesting consensus data per epochs for rewards

  This can be ran before or during a model activation.

  If before, it will wait until the subnet is successfully voted in, if the proposal to initialize the subnet fails,
  it will not stop running.

  If after, it will begin to validate and or attest epochs
  """
  def __init__(self, path: str, authorizer: None, substrate: SubstrateConfigCustom):
    super().__init__()
    assert path is not None, "path must be specified"
    assert substrate is not None, "account_id must be specified"
    self.subnet_id = None # Not required in case of not initialized yet
    self.path = path
    self.subnet_accepting_consensus = False
    self.subnet_node_eligible = False
    self.subnet_activated = 9223372036854775807 # max int
    self.last_validated_or_attested_epoch = 0
    self.authorizer = authorizer

    self.substrate_config = substrate
    self.account_id = substrate.account_id

    self.previous_epoch_data = None

    # blockchain constants
    self.epoch_length = int(str(get_epoch_length(self.substrate_config.interface)))

    self.stop = threading.Event()

    # self.start()

  def run(self):
    # while True:
    while not self.stop.is_set():
      try:
        # get epoch
        block_number = get_block_number(self.substrate_config.interface)

        logger.info("Block height: %s " % block_number)

        epoch = int(block_number / self.epoch_length)
        logger.info("Epoch: %s " % epoch)

        next_epoch_start_block = get_next_epoch_start_block(
          self.epoch_length, 
          block_number
        )
        remaining_blocks_until_next_epoch = next_epoch_start_block - block_number

        print("epoch <= self.last_validated_or_attested_epoch", epoch <= self.last_validated_or_attested_epoch, self.account_id)
        print("epoch <= self.last_validated_or_attested_epoch and self.subnet_accepting_consensus", epoch <= self.last_validated_or_attested_epoch and self.subnet_accepting_consensus, self.account_id)
        print("self.subnet_accepting_consensus", self.subnet_accepting_consensus, self.account_id)

        # skip if already validated or attested epoch
        if epoch <= self.last_validated_or_attested_epoch and self.subnet_accepting_consensus:
          logger.info("Already completed epoch: %s, waiting for the next %s " % (epoch, self.account_id))
          time.sleep(BLOCK_SECS * 2)
          continue

        # Ensure subnet is activated
        if self.subnet_accepting_consensus == False:
          logger.info("Waiting for subnet activation")
          activated = self._activate_subnet()

          # if given shutdown flag
          # ``_activate_subnet(self)`` can shutdown if the subnet is Null
          if self.stop.is_set():
            logger.info("Consensus thread shutdown, stopping consensus")
            break

          if activated == True:
            continue
          else:
            # Sleep until voting is complete
            time.sleep(BLOCK_SECS * 2)
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
          submittable_nodes = get_submittable_nodes(
            self.substrate_config.interface,
            self.subnet_id,
          )

          #  wait until we are submittable
          for node_set in submittable_nodes:
            if node_set.account_id == self.account_id:
              self.subnet_node_eligible = True
              break
          
          if self.subnet_node_eligible == False:
            logger.info("Node not eligible for consensus, sleeping until next epoch")
            time.sleep(BLOCK_SECS * 2)
            continue

        # is epoch submitted yet

        # is validator?
        validator = self._get_validator(epoch)
        print("validator", validator)

        # a validator is not chosen if there are not enough nodes, or the subnet is deactivated
        if validator == None:
          logger.info("Validator not chosen for epoch %s yet, checking next block" % epoch)
          time.sleep(BLOCK_SECS * 2)
          continue
        else:
          logger.info("Validator for epoch %s is %s" % (epoch, validator))

        is_validator = validator == self.account_id
        print("is_validator", is_validator, self.account_id)
        if is_validator:
          logger.info("We're the chosen validator for epoch %s, validating and auto-attesting..." % epoch)
          # check if validated already just in case
          validated = self._get_validator_consensus_submission(epoch)
          print("validated", validated, self.account_id)

          if validated == None:
            print("validated == None", self.account_id)
            success = self.validate()
            print("success = self.validate()", success, self.account_id)
            # update last validated epoch and continue (this validates and attests in one call)
            if success:
              logger.info("Successfully validate epoch %s" % epoch)
              self.last_validated_or_attested_epoch = epoch
            else:
              logger.warning("Consensus submission unsuccessful, waiting until next block to try again")
          else:
            print("last_validated_or_attested_epoch = epoch", epoch, self.account_id)
            # if for any reason on the last attempt it succeeded but didn't propogate
            # because this section should only be called once per epoch and if validator until successful submission of data
            self.last_validated_or_attested_epoch = epoch

          print("continue to next epoch, no need to attest")
          # continue to next epoch, no need to attest
          time.sleep(BLOCK_SECS)
          continue

        # we are not validator, we must attest or not attest
        # wait until validated by epochs chosen validator

        # get epoch before waiting for validator to validate to ensure we don't get stuck 
        initial_epoch = epoch
        logger.info("Starting attestation check")
        attest_attempts = 0
        MAX_ATTEST_ATTEMPTS = 3
        while True:
          # wait for validator on every block
          time.sleep(BLOCK_SECS * 2)
          block_number = get_block_number(self.substrate_config.interface)
          logger.warning("In Attest block %s" % self.account_id)
          logger.info("Block height: %s " % block_number)

          epoch = int(block_number / self.epoch_length)
          logger.info("Epoch: %s " % epoch)

          next_epoch_start_block = get_next_epoch_start_block(
            self.epoch_length, 
            block_number
          )
          remaining_blocks_until_next_epoch = next_epoch_start_block - block_number

          # If we made it to the next epoch, break
          # This likely means the chosen validator never submitted consensus data
          if epoch > initial_epoch:
            logger.info("Validator didn't submit epoch %s consensus data, moving to the next epoch" % epoch)
            break

          attest_result, reason = self.attest(epoch)
          print("attest_result", attest_result, self.account_id)
          print("reason", reason, self.account_id)

          if attest_result == False:
            attest_attempts += 1
            print("attest_attempts", attest_attempts, self.account_id)

            if reason == AttestReason.WAITING or reason == AttestReason.ATTEST_FAILED:
              logger.info("AttestReason.WAITING or AttestReason.ATTEST_FAILED")
              continue
            elif reason == AttestReason.ATTESTED:
              # An impossible scenario, but why not?
              logger.info("Already attested")
              self.last_validated_or_attested_epoch = epoch
              break
            elif reason == AttestReason.SHOULD_NOT_ATTEST:
              logger.warning("AttestReason.SHOULD_NOT_ATTEST")
              # sleep until end of epoch to check if we should attest
              """
              IF:
               1. Validator submits data
               2. Node leaves subnet on the same block
              """
              continue
            # If False, still waiting for validator to submit data
            continue
          else:
            # successful attestation, break and go to next epoch
            logger.info("Successfully attested epoch %s" % epoch)
            self.last_validated_or_attested_epoch = epoch
            break
      except Exception as e:
        logger.error("Consensus Error: %s" % e, exc_info=True)

  def validate(self) -> bool:
    print("validate", self.account_id)
    """Get rewards data and submit consensus"""
    # TODO: Add exception handling
    consensus_data = self._get_consensus_data()
    return self._do_validate(consensus_data["peers"])

  def attest(self, epoch: int) -> Tuple[bool, AttestReason]:
    """Get rewards data from another validator and attest that data if valid"""
    validator_consensus_submission = self._get_validator_consensus_submission(epoch)

    print("attest validator_consensus_submission", validator_consensus_submission)

    if validator_consensus_submission == None:
      logger.info("Waiting for validator to submit")
      return False, AttestReason.WAITING

    # backup check if validator node restarts in the middle of an epoch to ensure they don't tx again
    if self._has_attested(validator_consensus_submission["attests"]):
      logger.info("Has attested already")
      return False, AttestReason.ATTESTED
    
    validator_consensus_data = RewardsData.list_from_scale_info(validator_consensus_submission["data"])
    
    logger.info("Checking if we should attest the validators submission")
    logger.info("Generating consensus data")
    consensus_data = self._get_consensus_data() # should always return `peers` key
    should_attest = self.should_attest(validator_consensus_data, consensus_data["peers"], epoch)
    logger.info("Should attest is: %s", should_attest)

    if should_attest:
      logger.info("Validators data is confirmed valid, attesting data...")
      attest_is_success = self._do_attest()
      if attest_is_success:
        return True, AttestReason.ATTESTED
      else:
        return False, AttestReason.ATTEST_FAILED
    else:
      logger.info("Validators data is not valid, skipping attestation.")
      return False, AttestReason.SHOULD_NOT_ATTEST
    
  def _do_validate(self, data) -> bool:
    print("_do_validate", self.account_id)
    print("_do_validate last_validated_or_attested_epoch", self.last_validated_or_attested_epoch, self.account_id)
    try:
      receipt = validate(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        self.subnet_id,
        data
      )
      print("_do_validate receipt.error_message", receipt.error_message)
      print("_do_validate receipt.is_success", receipt.is_success)
      return receipt.is_success
    except Exception as e:
      logger.error("Validation Error: %s" % e)
      return False

  def _do_attest(self) -> bool:
    print("_do_attest", self.account_id)
    print("_do_attest self.subnet_id", self.subnet_id)
    print("_do_attest last_validated_or_attested_epoch", self.last_validated_or_attested_epoch, self.account_id)

    try:
      receipt = attest(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        self.subnet_id,
      )
      print("_do_attest receipt.error_message", receipt.error_message)
      print("_do_attest receipt.is_success", receipt.is_success)
      return receipt.is_success
    except Exception as e:
      logger.error("Attestation Error: %s" % e)
      return False
    
  def _get_consensus_data(self):
    print("_get_consensus_data", self.account_id)
    result = get_subnet_nodes_included(
      self.substrate_config.interface,
      self.subnet_id
    )

    subnet_nodes_data = SubnetNode.list_from_vec_u8(result["result"])

    # check test PEER_IDS versus 
    # filter PEER_IDS that don't match onchain subnet nodes
    peer_set = set(PEER_IDS)

    filtered_list = [d.peer_id for d in subnet_nodes_data if d.peer_id in peer_set]

    consensus_data = []
    for peer_id in filtered_list:
      node = {
        'peer_id': peer_id,
        'score': 10000
      }
      consensus_data.append(node)

    consensus_data = {
      "model_state": "healthy",
      "peers": consensus_data
    }

    return consensus_data

  def _get_validator_consensus_submission(self, epoch: int):
    """Get and return the consensus data from the current validator"""
    rewards_submission = get_rewards_submission(
      self.substrate_config.interface,
      self.subnet_id,
      epoch
    )
    return rewards_submission

  def _has_attested(self, attestations) -> bool:
    print("_has_attested")
    """Get and return the consensus data from the current validator"""
    for data in attestations:
      print("_has_attested data", data)
      if data[0] == self.account_id:
        logger.warning("_has_attested already attested %s" % self.account_id)
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
    TODO: Accuracy on sleep based on reg blocks

    Will wait for subnet to be activated

    1. Check if subnet activated
    2. If not activated, calculate turn to activate based on peer index
    3. Wait for the turn to activate to pass

    Returns:
      bool: True if subnet was successfully activated, False otherwise.
    """
    subnet_id = get_subnet_id_by_path(self.substrate_config.interface, self.path)
    if subnet_id.meta_info['result_found'] is False:
      logger.error("Cannot find subnet ID at path: %s, shutting down", self.path)
      self.shutdown()
      return False
    
    subnet_data = get_subnet_data(
      self.substrate_config.interface,
      int(str(subnet_id))
    )
    if subnet_data.meta_info['result_found'] is False:
      logger.error("Cannot find subnet data at ID: %s, shutting down", subnet_id)
      self.shutdown()
      return False

    initialized = int(str(subnet_data['initialized']))
    registration_blocks = int(str(subnet_data['registration_blocks']))
    activation_block = initialized + registration_blocks

    # if we didn't activate the subnet, someone indexed before us should have - see logic below
    if subnet_data['activated'] > 0:
      self.subnet_accepting_consensus = True
      self.subnet_id = int(str(subnet_id))
      self.subnet_activated = int(str(subnet_data["activated"]))
      logger.info("Subnet activated")
      return True

    # the following logic is for registering subnets with nodes waiting to activate the subnet onchain

    # randomize activating subnet by node entry index
    # when subnet is in registration, all new subnet nodes are ``Submittable`` classification
    # so we check all submittable nodes
    submittable_nodes = get_submittable_nodes(
      self.substrate_config.interface,
      int(str(subnet_id)),
    )

    submittable = False
    n = 0
    for node_set in submittable_nodes:
      n+=1
      if node_set.account_id == self.account_id:
        submittable = True
        break
    
    # redundant
    # if we made it this far and the node is not yet activated, the subnet should be activated
    if not submittable:
      logger.warning("Not submittable yet, must activate node on-chain")
      time.sleep(BLOCK_SECS)
      self._activate_subnet()
    
    min_node_activation_block = activation_block + BLOCK_SECS*10 * (n-1)
    max_node_activation_block = activation_block + BLOCK_SECS*10 * n

    block_number = get_block_number(self.substrate_config.interface)

    # If outside of activation period on both ways
    if block_number < min_node_activation_block:
      logger.info("Subnet not activated yet, waiting for our turn to attempt activation at block %s" % min_node_activation_block)
      delta = min_node_activation_block - block_number
      time.sleep(BLOCK_SECS)
      self._activate_subnet()
    
    # someone of me should have activated by now, keep iterating
    # this will print a warning to manually activate
    if block_number >= max_node_activation_block:
      logger.warning("We skipped subnet activation, attempt to manually activate")
      time.sleep(BLOCK_SECS)
      self._activate_subnet()


    # if within our designated activation block, then activate
    # activation is a no-weight transaction, meaning it costs nothing to do
    if block_number >= min_node_activation_block and block_number < max_node_activation_block:
      logger.info("Activating subnet in our block range")
      # check if activated already by another node
      subnet_data = get_subnet_data(
        self.substrate_config.interface,
        int(str(subnet_id))
      )

      # check if already activated
      if subnet_data['activated'] > 0:
        self.subnet_accepting_consensus = True
        self.subnet_id = int(str(subnet_id))
        self.subnet_activated = True
        logger.info("Subnet activated")
        return True

      # Attempt to activate subnet
      # at this point we assume the subnet is not activated yet
      logger.info("Attempting to activate subnet")
      receipt = activate_subnet(
        self.substrate_config.interface,
        self.substrate_config.keypair,
        int(str(subnet_id)),
      )

      if receipt == None:
        logger.warning("`activate_subnet` Extrinsic failed: Subnet activation failed, check if activated")
        return False

      if receipt.is_success != True:
        logger.warning("`activate_subnet` Extrinsic failed: Subnet activation failed, check if activated")
        return False

      is_success = False
      for event in receipt.triggered_events:
        event_id = event.value['event']['event_id']
        print("\n event_id == 'SubnetActivated'", event_id == 'SubnetActivated')
        if event_id == 'SubnetActivated':
          logger.info("Subnet activation successful")
          is_success = True
          break
        
      if is_success:
        self.subnet_accepting_consensus = True
        self.subnet_id = int(str(subnet_id))
        self.subnet_activated = True
        return True
      else:
        logger.warning("Subnet activation failed, subnet didn't meet requirements")

    # check if subnet failed to be activated
    # this means:
    # someone else activated it and code miscalculated (contact devs with error if so)
    # or the subnet didn't meet its activation requirements and should revert on the next ``_activate_subnet`` call
    return False

  def should_attest(self, validator_data, my_data, epoch):
    """Checks if two arrays of dictionaries match, regardless of order."""

    # if validator submitted no data, and we have also found the subnet is broken
    if len(validator_data) == 0 and len(my_data) == 0:
      return True
    
    # otherwise, check the data matches
    # at this point, the
    
    # use ``asdict`` because data is decoded from blockchain as dataclass
    # we assume the lists are consistent across all elements
    # Convert validator_data to a set
    set1 = set(frozenset(asdict(d).items()) for d in validator_data)

    # Convert my_data to a set
    set2 = set(frozenset(d.items()) for d in my_data)

    success = set1 == set2

    """
    The following accounts for nodes that go down or back up in the after or before validation submissions and attestations
    - If nodes leaves DHT before before validator submit consensus and returns after before attestation
    - If node leaves DHT after validator submits consensus but still available on the blockchain
    We check the previous epochs data to see if the validator did submit before they left
    """
    if not success and self.previous_epoch_data is not None:
      dif = set1.symmetric_difference(set2)
      print("should_attest if 1 dif: ", dif)

      success = dif.issubset(self.previous_epoch_data)
    elif not success and self.previous_epoch_data is None:
      """
      If this is the nodes first epoch, check last epochs consensus data
      """
      previous_epoch_validator_data = self._get_validator_consensus_submission(epoch-1)
      if previous_epoch_validator_data != None:
        previous_epoch_data_onchain = set(frozenset(asdict(d).items()) for d in previous_epoch_validator_data)
        dif = set1.symmetric_difference(set2)
        print("should_attest elif previous_epoch_validator_data: ", previous_epoch_validator_data)
        print("should_attest elif previous_epoch_data_onchain: ", previous_epoch_data_onchain)
        print("should_attest elif dif: ", dif)

        success = dif.issubset(previous_epoch_data_onchain)
    else:
      intersection = set1.intersection(set2)
      print("should_attest else: ", intersection)
      logger.info("Matching intersection of %s validator data" % (safe_div(len(intersection), len(set1)) * 100))
      logger.info("Validator matching intersection of %s my data" % (safe_div(len(intersection), len(set2)) * 100))

    self.previous_epoch_data = set2

    return success

  def shutdown(self):
    self.stop.set()

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

