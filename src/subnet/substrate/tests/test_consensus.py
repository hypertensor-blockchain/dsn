import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass, asdict
from typing import List

# python src/subnet/substrate/tests/test_consensus.py

@dataclass
class ValidatorEntry:
  peer_id: str
  score: int

class TestValidatorAttestation(unittest.TestCase):
    
  def setUp(self):
    """Set up the attestation system for each test case"""
    self.attestation = AttestationSystem()
  
  def test_exact_match(self):
    """Test when validator data and my data match exactly"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}, {"peer_id": "456", "score": 1}]

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 1))

  def test_no_data_and_broken_subnet(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_no_data_and_broken_subnet
    """
    """Test when both validator and my data are empty"""
    validator_data = []
    my_data = []

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 1))

  def test_validator_incorrect_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_incorrect_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = [{"peer_id": "123", "score": 2}]  # Different score

    self.assertFalse(self.attestation.should_attest(validator_data, my_data, 1))

  def test_validator_incorrect_data_2(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_incorrect_data_2
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data, 1))

  def test_validator_extra_validator_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_extra_validator_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1), ValidatorEntry("789", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data, 1))

  def test_attestor_extra_attestor_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_attestor_extra_attestor_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}, { "peer_id": "789", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data, 1))

  def test_validator_should_attest_same_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_should_attest_same_data
    """
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 1))

  def test_first_epoch_uses_previous_validator_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_first_epoch_uses_previous_validator_data
    """
    """Test first epoch where previous data is checked from validator submission"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = []

    # Mock function to return validator data from last epoch
    self.attestation._get_validator_consensus_submission = MagicMock(
        return_value=[ValidatorEntry("123", 1)]
    )

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 1))

  def test_validator_correct_but_node_leaves_after_submission(self):
    """Test when a node leaves after validator submits correctly"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = []

    # Last epoch had the node, meaning the validator was honest
    self.attestation.previous_epoch_data = {frozenset({"peer_id": "123", "score": 1}.items())}

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 2))

  def test_validator_correct_but_node_leaves_after_submission_2(self):
    """Test when a node leaves after validator submits correctly"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}]

    # Last epoch had the node, meaning the validator was honest
    self.attestation.previous_epoch_data = {frozenset({"peer_id": "456", "score": 1}.items())}

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 2))

  def test_validator_incorrect_but_node_leaves_after_submission(self):
    """Node leaves but validator submitted validator not in previous epochs data"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "456", "score": 1}]

    # Last epoch had the node, meaning the validator was honest
    self.attestation.previous_epoch_data = {frozenset({"peer_id": "456", "score": 1}.items())}

    self.assertFalse(self.attestation.should_attest(validator_data, my_data, 2))

  def test_previous_epoch_check_for_validator_honesty(self):
    """Test when previous epoch data needs to be checked to verify validator honesty"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "456", "score": 1}]  # Different node available

    # Previous epoch had "123" meaning validator was honest
    self.attestation.previous_epoch_data = {frozenset({"peer_id": "123", "score": 1}.items())}

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 2))

  def test_validator_correct_but_node_leaves_before_submission_returns_after(self):
    """Test when a node leaves before validator submits correctly and returns after, but before attestors attest"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = [{"peer_id": "123", "score": 1}, {"peer_id": "456", "score": 1}]

    # Last epoch had the node, meaning the validator was honest
    self.attestation.previous_epoch_data = {frozenset({"peer_id": "123", "score": 1}.items()), frozenset({"peer_id": "456", "score": 1}.items())}

    self.assertTrue(self.attestation.should_attest(validator_data, my_data, 2))

# Mock the AttestationSystem class with required methods
class AttestationSystem:
  def __init__(self):
    self.previous_epoch_data = None
  
  def _get_validator_consensus_submission(self, epoch):
    """Mock method to return previous epoch validator data"""
    return self.previous_epoch_data  # Default case, overridden in tests

  def _get_reward_result(self, epoch):
    """Mock method to return previous epoch validator data"""
    return self.previous_epoch_data

  def should_attest(self, validator_data: List[ValidatorEntry], my_data: List[dict], epoch: int) -> bool:
    """Actual function logic copied from the provided implementation"""
    
    if len(validator_data) == 0 and len(my_data) == 0:
        return True

    set1 = set(frozenset(asdict(d).items()) for d in validator_data)
    set2 = set(frozenset(d.items()) for d in my_data)

    success = set1 == set2

    # if not success and self.previous_epoch_data is not None:
    #   print("Block 2 hit")
    #   dif = set1.symmetric_difference(set2)
    #   success = dif.issubset(self.previous_epoch_data)
    # elif not success and self.previous_epoch_data is None:
    #   print("Block 3 hit")
    #   previous_epoch_validator_data = self._get_validator_consensus_submission(epoch - 1)
    #   if previous_epoch_validator_data is not None:
    #     print("Block 4 hit")
    #     previous_epoch_data_onchain = set(frozenset(asdict(d).items()) for d in previous_epoch_validator_data)
    #     dif = set1.symmetric_difference(set2)
    #     success = dif.issubset(previous_epoch_data_onchain)

    if not success and self.previous_epoch_data is not None:
      dif = set1.symmetric_difference(set2)
      success = dif.issubset(self.previous_epoch_data)
    elif not success and self.previous_epoch_data is None:
      previous_epoch_validator_data = self._get_validator_consensus_submission(epoch-1)
      # This is a backup so we ensure the data was super majority attested to use it
      if previous_epoch_validator_data != None:
        _, attestation_percentage = self._get_reward_result(epoch)
        previous_epoch_data_onchain = set(frozenset(asdict(d).items()) for d in previous_epoch_validator_data)
        dif = set1.symmetric_difference(set2)
        success = dif.issubset(previous_epoch_data_onchain)
    else:
      # log only data
      intersection = set1.intersection(set2)

    self.previous_epoch_data = set2
    return success

  def should_attest_old(self, validator_data: List[ValidatorEntry], my_data: List[dict], epoch: int) -> bool:
    return True

# Run the tests
if __name__ == "__main__":
  unittest.main()
