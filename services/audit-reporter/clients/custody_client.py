import os
from typing import Any

from clients.base import _correlation_headers, _get

_BASE_URL: str = os.environ["CUSTODY_SERVICE_URL"]


async def get_timeline(
    artifact_id: str, *, actor_id: str, actor_role: str, corr_id: str
) -> dict[str, Any]:
    url = f"{_BASE_URL}/custody/{artifact_id}/timeline"
    headers = _correlation_headers(actor_id, actor_role, corr_id)
    return await _get(url, headers, "custody-service")
