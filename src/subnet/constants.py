import torch

PUBLIC_INITIAL_PEERS = [
]

# The reachability API is currently used only when connecting to the public swarm
REACHABILITY_API_URL = "https://dash.hypertensor.org"

DTYPE_MAP = dict(bfloat16=torch.bfloat16, float16=torch.float16, float32=torch.float32, auto="auto")

"""
tmp file for storing initial peers (should be replaced logically)
this helps with first-in nodes that have no initial peers listed so they can connect to the dht
nodes can manually update this file if needed as well
its likely best to use subnet smart contracts instead but this is an option
"""
TEMP_INITIAL_PEERS_LOCATION = "tmp/initial-peers"