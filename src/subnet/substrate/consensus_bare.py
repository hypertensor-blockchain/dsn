from dataclasses import asdict
from enum import Enum
import threading
import time
from typing import Optional, Tuple

from hypermind.utils.auth import AuthorizerBase

from subnet.health.state_updater import ScoringProtocol
from subnet.substrate.chain_data import RewardsData
from subnet.substrate.chain_functions import activate_subnet, attest, get_block_number, get_epoch_length, get_reward_result_event, get_subnet_data, get_subnet_id_by_path, get_rewards_submission, get_rewards_validator, validate
from subnet.substrate.config import BLOCK_SECS, SubstrateConfigCustom
from subnet.substrate.utils import get_included_nodes, get_consensus_data, get_next_epoch_start_block, get_submittable_nodes
from hypermind.utils import get_logger

from subnet.utils.math import saturating_div, saturating_sub

logger = get_logger(__name__)

MAX_ATTEST_CHECKS = 3

class AttestReason(Enum):
  WAITING = 1
  ATTESTED = 2
  ATTEST_FAILED = 3
  SHOULD_NOT_ATTEST = 4

class Consensus(threading.Thread):
  """
  Houses logic for validating and attesting consensus data per epochs for rewards

  This can be ran before or during a model activation.

  If before, it will wait until the subnet is successfully voted in, if the proposal to initialize the subnet fails,
  it will not stop running.

  If after, it will begin to validate and or attest epochs
  """
  def __init__(
      self, 
      path: str, 
      authorizer: AuthorizerBase, 
      identity_path: str
    ):
    super().__init__()
    assert path is not None, "path must be specified"
    self.subnet_id = None # Not required in case of not initialized yet
    self.path = path
    self.subnet_accepting_consensus = False
    self.subnet_node_eligible = False
    self.subnet_activated = 9223372036854775807 # max int
    self.last_validated_or_attested_epoch = 0
    self.authorizer = authorizer

    self.previous_epoch_data = None

    # initialize DHT client for scoring protocol
    self.scoring_protocol = ScoringProtocol(self.authorizer, identity_path)

    self.stop = threading.Event()

    self.start()

  def run(self):
    """
    Iterates each epoch, runs the incentives mechanism for the SCP
    """
    while not self.stop.is_set():
      try:
        peers_data = self.scoring_protocol.run()
        print("peers_data: ", peers_data)
        time.sleep(BLOCK_SECS)
      except Exception as e:
        logger.error("Consensus Bare Error: %s" % e, exc_info=True)

  def shutdown(self):
    self.stop.set()
