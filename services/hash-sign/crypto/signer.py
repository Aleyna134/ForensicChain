import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

_PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "/keys/private_key.pem")
_PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH", "/keys/public_key.pem")

# Load keys once at module import — avoids per-call file I/O and PEM parsing.
with open(_PRIVATE_KEY_PATH, "rb") as _f:
    _private_key = load_pem_private_key(_f.read(), password=None)

with open(_PUBLIC_KEY_PATH, "rb") as _f:
    _public_key = load_pem_public_key(_f.read())


def sign_hash(hash_hex: str) -> str:
    """
    Signs a SHA-256 hash (hex string) with the RSA private key.
    Returns: base64-encoded RSA signature.
    """
    signature = _private_key.sign(
        hash_hex.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(hash_hex: str, signature_base64: str) -> bool:
    """
    Verifies a base64-encoded RSA signature against a hash value.
    Returns True if valid, False otherwise.
    """
    try:
        _public_key.verify(
            base64.b64decode(signature_base64),
            hash_hex.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
