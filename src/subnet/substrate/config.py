"""
Substrate config file for storing blockchain configuration and parameters in a pickle
to avoid remote blockchain calls
"""
from substrateinterface import SubstrateInterface, Keypair

BLOCK_SECS = 6

class SubstrateConfigCustom:
  def __init__(self, phrase, url):
    self.url = url
    self.interface: SubstrateInterface = SubstrateInterface(url=url)
    self.keypair = Keypair.create_from_uri(phrase)
    self.hotkey = Keypair.create_from_uri(phrase).ss58_address