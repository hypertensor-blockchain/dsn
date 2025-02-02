import re
from typing import Any


def extract_key(record) -> Any:
  """
  Extracts the subkey from a validator subkey in a DHTRecord based on the Ed25519SignatureValidator

  Args:
    record (Any): Key or subkey.

  Returns:
    Any: The key or subkey value with no public key.

  Example:
    >>> extract_key(b'12D3KooWMRSF23cFaFPTM9YTz712BSntSY5WmA88Db12E9NqtT8S[owner:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKxsfZtGahRIqt4vipY6wmjxbVM0AXTexeSuzzOJGznv]')
    b'12D3KooWMRSF23cFaFPTM9YTz712BSntSY5WmA88Db12E9NqtT8S'
  """

  if isinstance(record, bytes):
    # Define the regex pattern to match the value before the '[owner:...]'
    pattern = b'^(.*?)\[owner:'

    # Use re.search to find the match
    match = re.search(pattern, record)

    # Extract the value if a match is found
    if match:
        value = match.group(1)
        return value
    else:
      return record
  else:
    return record
