import hashlib
import json
from typing import Tuple, Optional, Any

def compute_payload_hash(raw_payload: dict) -> str:
    """
    Computes the SHA-256 hash of a JSON-serializable payload dictionary.
    Keys are sorted to ensure consistent serialization.
    """
    payload_bytes = json.dumps(raw_payload, sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload_bytes).hexdigest()

def compute_record_hash(payload_hash: str, previous_record_hash: Optional[str]) -> str:
    """
    Computes the SHA-256 hash for the ledger record chain.
    If previous_record_hash is provided, it concatenates payload_hash + previous_record_hash.
    If not (genesis record), it hashes payload_hash + "GENESIS".
    """
    if previous_record_hash:
        data_to_hash = f"{payload_hash}{previous_record_hash}"
    else:
        data_to_hash = f"{payload_hash}GENESIS"
        
    return hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()

def create_hash_chain_entry(raw_payload: dict, previous_record_hash: Optional[str]) -> Tuple[str, str]:
    """
    Helper to compute both payload_hash and record_hash.
    """
    payload_hash = compute_payload_hash(raw_payload)
    record_hash = compute_record_hash(payload_hash, previous_record_hash)
    return payload_hash, record_hash
