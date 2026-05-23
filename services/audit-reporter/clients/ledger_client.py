import os
from typing import Any, Optional

from clients.base import _correlation_headers, _get, _get_optional

_BASE_URL: str = os.environ["LEDGER_SERVICE_URL"]


async def get_proof(
    artifact_id: str, *, actor_id: str, actor_role: str, corr_id: str
) -> dict[str, Any]:
    url = f"{_BASE_URL}/ledger/artifacts/{artifact_id}"
    headers = _correlation_headers(actor_id, actor_role, corr_id)
    return await _get(url, headers, "ledger-service")


async def get_proof_optional(
    artifact_id: str, *, actor_id: str, actor_role: str, corr_id: str
) -> Optional[dict[str, Any]]:
    """Returns the artifact's ledger proof, or None if no proof record exists yet."""
    url = f"{_BASE_URL}/ledger/artifacts/{artifact_id}"
    headers = _correlation_headers(actor_id, actor_role, corr_id)
    return await _get_optional(url, headers, "ledger-service")


async def get_validation(
    case_id: str, *, actor_id: str, actor_role: str, corr_id: str
) -> dict[str, Any]:
    url = f"{_BASE_URL}/ledger/validate/{case_id}"
    headers = _correlation_headers(actor_id, actor_role, corr_id)
    return await _get(url, headers, "ledger-service")


async def get_records(
    case_id: str, *, actor_id: str, actor_role: str, corr_id: str
) -> list[dict[str, Any]]:
    url = f"{_BASE_URL}/ledger/records/{case_id}"
    headers = _correlation_headers(actor_id, actor_role, corr_id)
    return await _get(url, headers, "ledger-service")
