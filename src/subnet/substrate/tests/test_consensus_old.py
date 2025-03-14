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

    self.assertTrue(self.attestation.should_attest(validator_data, my_data))

  def test_no_data_and_broken_subnet(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_no_data_and_broken_subnet
    """
    """Test when both validator and my data are empty"""
    validator_data = []
    my_data = []

    self.assertTrue(self.attestation.should_attest(validator_data, my_data))

  def test_validator_incorrect_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_incorrect_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = [{"peer_id": "123", "score": 2}]  # Different score

    self.assertFalse(self.attestation.should_attest(validator_data, my_data))

  def test_validator_incorrect_data_2(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_incorrect_data_2
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data))

  def test_validator_extra_validator_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_extra_validator_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1), ValidatorEntry("789", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data))

  def test_attestor_extra_attestor_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_attestor_extra_attestor_data
    """
    """Test when validator submits incorrect data"""
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}, { "peer_id": "789", "score": 1}]

    self.assertFalse(self.attestation.should_attest(validator_data, my_data))

  def test_validator_should_attest_same_data(self):
    """
    python src/subnet/substrate/tests/test_consensus.py TestValidatorAttestation.test_validator_should_attest_same_data
    """
    validator_data = [ValidatorEntry("123", 1), ValidatorEntry("456", 1)]
    my_data = [{"peer_id": "123", "score": 1}, { "peer_id": "456", "score": 1}]

    self.assertTrue(self.attestation.should_attest(validator_data, my_data))

# Mock the AttestationSystem class with required methods
class AttestationSystem:
  def __init__(self):
    self.previous_epoch_data = None
  
  def _get_validator_consensus_submission(self, epoch):
    """Mock method to return previous epoch validator data"""
    return self.previous_epoch_data  # Default case, overridden in tests

  def should_attest(self, validator_data: List[ValidatorEntry], my_data: List[dict]):
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

    return set1 == set2

# Run the tests
if __name__ == "__main__":
  unittest.main()
