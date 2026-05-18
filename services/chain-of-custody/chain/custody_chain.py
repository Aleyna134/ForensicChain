import hashlib
import json


def compute_event_hash(event_content: dict) -> str:
    """
    Deterministically hash a custody event dict.

    All fields that describe WHAT happened and WHO did it are included so that
    any post-hoc modification (reason, ip_address, payload, actor, timestamp …)
    breaks the hash and makes tampering detectable.

    The dict must be produced by build_event_content() to guarantee a stable
    field set; callers must not pass raw message bodies directly.
    """
    canonical = json.dumps(event_content, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_event_content(
    *,
    event_id: str,
    event_type: str,
    artifact_id: str,
    case_id: str | None,
    actor_id: str,
    actor_role: str,
    timestamp: str,
    reason: str | None,
    ip_address: str | None,
    correlation_id: str | None,
    payload: dict,
    previous_event_hash: str | None,
) -> dict:
    """
    Build the canonical dict that is passed to compute_event_hash().

    Keeping construction and hashing separate makes it straightforward to
    log or inspect the exact data that was signed.
    """
    return {
        "event_id": event_id,
        "event_type": event_type,
        "artifact_id": artifact_id,
        "case_id": case_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timestamp,
        "reason": reason,
        "ip_address": ip_address,
        "correlation_id": correlation_id,
        "payload": payload,
        "previous_event_hash": previous_event_hash,
    }
