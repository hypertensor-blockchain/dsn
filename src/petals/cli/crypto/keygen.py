import argparse
import asyncio
import hashlib
import os

from hivemind.proto import crypto_pb2
from hivemind.p2p.p2p_daemon_bindings.datastructures import PeerID
from hivemind.utils.logging import get_logger
from hivemind.p2p.p2p_daemon import P2P

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives import serialization
import multihash

logger = get_logger(__name__)

# python -m petals.cli.crypto.keygen 

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--path", type=str, required=False, default="private_key.key", help="File location of private key. ")
    parser.add_argument("--key_type", type=str, required=False, default="ed25519", help="Key type used in subnet. ed25519, rsa")

    args = parser.parse_args()

    path = args.path
    key_type = args.key_type.lower()

    if key_type is "rsa":
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
    elif key_type == "ed25519":
        logger.info("Generating Ed25519 private key")
        private_key = ed25519.Ed25519PrivateKey.generate()

        raw_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,  # DER format
            format=serialization.PrivateFormat.Raw,  # PKCS8 standard format
            encryption_algorithm=serialization.NoEncryption()  # No encryption
        )

        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        combined_key_bytes = raw_private_key + public_key

        protobuf = crypto_pb2.PrivateKey(key_type=crypto_pb2.KeyType.Ed25519, data=combined_key_bytes)


        with open(path, "wb") as f:
            f.write(protobuf.SerializeToString())

        os.chmod(path, 0o400)
        with open(path, "rb") as f:
            data = f.read()
            key_data = crypto_pb2.PrivateKey.FromString(data).data

            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data[:32])

            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

            combined_key_bytes = private_key.private_bytes_raw() + public_key

            encoded_public_key = crypto_pb2.PublicKey(
                key_type=crypto_pb2.Ed25519,
                data=public_key,
            ).SerializeToString()

            encoded_digest = b"\x00$" + encoded_public_key
            print("encoded_digest", encoded_digest)

            peer_id = PeerID(encoded_digest)
            print("peer_id", peer_id)

            peer_id_to_bytes = peer_id.to_bytes()
            print("peer_id_to_bytes", peer_id_to_bytes)

            assert peer_id == peer_id_to_bytes
    else:
        raise ValueError("Invalid key type. Supported types: rsa, ed25519")

    peer_id = PeerID(encoded_digest)
    logger.info(f"Peer ID {peer_id}")

    async def test_identity():
        p2p = await P2P.create(identity_path=path)
        p2p_peer_id = p2p.peer_id
        print("p2p_peer_id", p2p_peer_id)

        await p2p.shutdown()

        return p2p_peer_id

    p2p_peer_id = asyncio.run(test_identity())

    assert peer_id.__eq__(p2p_peer_id), "Generated Peer ID and subnet Peer ID are not equal"

if __name__ == "__main__":
    main()
