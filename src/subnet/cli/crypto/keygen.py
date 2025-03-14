import argparse
import asyncio
import hashlib
import os

from hypermind.proto import crypto_pb2
from hypermind.p2p.p2p_daemon_bindings.datastructures import PeerID
from hypermind.utils.logging import get_logger
from hypermind.p2p.p2p_daemon import P2P

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives import serialization
import multihash

logger = get_logger(__name__)

# python -m subnet.cli.crypto.keygen 
# python -m subnet.cli.crypto.keygen --path private_key.key --bootstrap_path bootstrap_private_key.key
# python -m subnet.cli.crypto.keygen --path private_key2.key --bootstrap_path bootstrap_private_key2.key

def generate_rsa_private_key(path: str):
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
        logger.info(f"DER RSA Public Key: {encoded_public_key}")

        encoded_public_key = crypto_pb2.PublicKey(
            key_type=crypto_pb2.RSA,
            data=encoded_public_key,
        ).SerializeToString()

        encoded_digest = multihash.encode(
            hashlib.sha256(encoded_public_key).digest(),
            multihash.coerce_code("sha2-256"),
        )
    return encoded_digest

def generate_ed25519_private_key(path: str):
    logger.info(f"Generating Ed25519 private key to {path}")
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
    logger.info(f"Raw Ed25519 Public Key: {public_key}")

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

        peer_id = PeerID(encoded_digest)

        peer_id_to_bytes = peer_id.to_bytes()

        assert peer_id == peer_id_to_bytes

    return encoded_digest

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--path", type=str, required=False, default="private_key.key", help="File location of private key. ")
    parser.add_argument("--bootstrap_path", type=str, required=False, default="bootstrap_private_key.key", help="File location of bootstrap private key. ")
    parser.add_argument("--key_type", type=str, required=False, default="ed25519", help="Key type used in subnet. ed25519, rsa")

    args = parser.parse_args()

    path = args.path
    bootstrap_path = args.bootstrap_path
    key_type = args.key_type.lower()

    if key_type is "rsa":
        encoded_digest = generate_rsa_private_key(path)
        bootstrap_encoded_digest = generate_rsa_private_key(bootstrap_path)
    elif key_type == "ed25519":
        encoded_digest = generate_ed25519_private_key(path)
        bootstrap_encoded_digest = generate_ed25519_private_key(bootstrap_path)
    else:
        raise ValueError("Invalid key type. Supported types: rsa, ed25519")

    peer_id = PeerID(encoded_digest)
    bootstrap_peer_id = PeerID(bootstrap_encoded_digest)
    logger.info(f"Peer ID {peer_id}")
    logger.info(f"Bootstrap Peer ID (Optional usage) {bootstrap_peer_id}")

    async def test_identity(identity_path: str):
        p2p = await P2P.create(identity_path=identity_path)
        p2p_peer_id = p2p.peer_id

        await p2p.shutdown()

        return p2p_peer_id

    p2p_peer_id = asyncio.run(test_identity(path))
    assert peer_id.__eq__(p2p_peer_id), "Generated Peer ID and subnet Peer ID are not equal"
    p2p_bootstrap_peer_id = asyncio.run(test_identity(bootstrap_path))
    assert bootstrap_peer_id.__eq__(p2p_bootstrap_peer_id), "Generated Bootstrap Peer ID and subnet Peer ID are not equal"

if __name__ == "__main__":
    main()
