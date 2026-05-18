from typing import Any

import httpx
from fastapi import HTTPException, status


def _correlation_headers(actor_id: str, actor_role: str, corr_id: str) -> dict[str, str]:
    return {
        "X-User-Id": actor_id,
        "X-User-Role": actor_role,
        "X-Correlation-Id": corr_id,
    }


async def _get(url: str, headers: dict[str, str], service_name: str) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{service_name} returned {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not reach {service_name}: {exc}",
            )
