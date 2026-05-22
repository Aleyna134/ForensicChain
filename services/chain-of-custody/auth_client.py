import logging
import os

import httpx

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8006")


async def get_assigned_case_numbers(username: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/internal/assignments/by-user/{username}"
            )
            if resp.status_code == 200:
                return resp.json().get("case_numbers", [])
    except Exception as exc:
        logger.warning("Failed to fetch assignments for %s: %s", username, exc)
    return []
