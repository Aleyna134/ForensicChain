import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

def sign_hash(hash_hex: str, private_key_path: str = "/keys/private_key.pem") -> str:
    """
    Signs a given SHA-256 hash (hex string) using the RSA private key.
    
    Args:
        hash_hex (str): The hex-encoded SHA-256 hash.
        private_key_path (str): Path to the PEM encoded private key.
        
    Returns:
        str: Base64-encoded RSA signature.
        
    Raises:
        FileNotFoundError: If the private key file does not exist.
        Exception: If key loading or signing fails.
    """
    if not os.path.exists(private_key_path):
        raise FileNotFoundError(f"Private key not found: {private_key_path}")
        
    with open(private_key_path, "rb") as key_file:
        private_key = load_pem_private_key(
            key_file.read(),
            password=None
        )
        
    # We sign the actual hash bytes (hex decoded) rather than the hex string,
    # or we can sign the UTF-8 encoded hex string itself.
    # Standard practice is to sign the raw bytes of the hash or the string representation.
    # Here we sign the string representation as it is passed around.
    data_to_sign = hash_hex.encode("utf-8")
    
    signature = private_key.sign(
        data_to_sign,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(hash_hex: str, signature_base64: str, public_key_path: str = "/keys/public_key.pem") -> bool:
    """
    Verifies a base64-encoded RSA signature against a hash value using the public key.
    
    Args:
        hash_hex (str): The expected hex-encoded SHA-256 hash.
        signature_base64 (str): The base64-encoded RSA signature.
        public_key_path (str): Path to the PEM encoded public key.
        
    Returns:
        bool: True if signature is valid, False otherwise.
    """
    if not os.path.exists(public_key_path):
        raise FileNotFoundError(f"Public key not found: {public_key_path}")
        
    try:
        with open(public_key_path, "rb") as key_file:
            public_key = load_pem_public_key(key_file.read())
            
        data_to_verify = hash_hex.encode("utf-8")
        signature_bytes = base64.b64decode(signature_base64)
        
        public_key.verify(
            signature_bytes,
            data_to_verify,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        # If verification fails, it will raise an exception from cryptography library
        # We catch it and return False, representing invalid signature
        print(f"Signature verification failed: {e}")
        return False
