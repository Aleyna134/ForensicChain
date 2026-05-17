import hashlib
import os

def compute_sha256(file_path: str) -> str:
    """
    Reads a file synchronously in chunks and computes its SHA-256 hash.
    
    Args:
        file_path (str): The absolute path to the file.
        
    Returns:
        str: Hex-encoded SHA-256 hash of the file.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()
    
    # Read the file in chunks to handle potentially large files
    with open(file_path, "rb") as f:
        # Read in 64K chunks
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest()
