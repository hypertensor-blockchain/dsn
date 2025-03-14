import hypermind
from health_v2_test import fetch_health_state2

logger = hypermind.get_logger(__name__)

PUBLIC_INITIAL_PEERS = ["/ip4/3.16.197.70/tcp/31330/p2p/12D3KooWNujrmWnkXz9Qr4WkPcEWUFgeqkgRKjymkrRUQHgWPFpC"]

# python src/subnet/health/state_updater_test.py

def get_peers_data():
    try:
        dht = hypermind.DHT(initial_peers=PUBLIC_INITIAL_PEERS, client_mode=False, num_workers=32, start=True)
        state_dict = fetch_health_state2(dht)
        return state_dict
    except Exception as error:
        logger.error("Failed to get peers data:", error)
        return None

get_peers_data()