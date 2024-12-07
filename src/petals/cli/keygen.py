import argparse
import asyncio
import hashlib
import logging
import configargparse

from hivemind.proto import crypto_pb2
from hivemind.p2p.p2p_daemon_bindings.datastructures import PeerID
from hivemind.utils.logging import get_logger
from hivemind.p2p.p2p_daemon import P2P

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import multihash

logger = get_logger(__name__)

# python -m petals.cli.keygen 

def main():
    print("running")
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--path", type=str, required=False, default="private_key_2.key", help="File location of private key")
    args = parser.parse_args()

    path = args.path

    # Generate the RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize the private key to DER format
    private_key = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    protobuf = crypto_pb2.PrivateKey(key_type=crypto_pb2.KeyType.RSA, data=private_key)

    with open(path, "wb") as f:
        f.write(protobuf.SerializeToString())

    with open(path, "rb") as f:
        data = f.read()
        key_data = crypto_pb2.PrivateKey.FromString(data).data

        private_key = serialization.load_der_private_key(key_data, password=None)

        encoded_public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        encoded_public_key = crypto_pb2.PublicKey(
            key_type=crypto_pb2.RSA,
            data=encoded_public_key,
        ).SerializeToString()

        encoded_digest = multihash.encode(
            hashlib.sha256(encoded_public_key).digest(),
            multihash.coerce_code("sha2-256"),
        )

        peer_id = PeerID(encoded_digest)

        logger.info(f"Peer ID {peer_id}")

    async def test_identity():
        p2p = await P2P.create(identity_path='private_key_2.key')
        p2p_peer_id = p2p.peer_id

        await p2p.shutdown()

        return p2p_peer_id

    p2p_peer_id = asyncio.run(test_identity())

    assert peer_id.__eq__(p2p_peer_id), "Peer ID mismatch"

if __name__ == "__main__":
    main()
