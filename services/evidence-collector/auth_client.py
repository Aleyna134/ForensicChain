import logging
import os

import httpx

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8006")
logger = logging.getLogger(__name__)


async def get_assigned_case_numbers(username: str) -> list[str]:
    """Returns active case_numbers assigned to username. Returns [] on any error (fail-safe)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AUTH_SERVICE_URL}/internal/assignments/by-user/{username}")
            if resp.status_code == 200:
                return resp.json().get("case_numbers", [])
    except Exception as exc:
        logger.warning("Failed to fetch assignments for %s: %s", username, exc)
    return []


async def case_is_open(case_number: str) -> bool:
    """Returns True if the case exists and is OPEN. Returns False on any error (fail-safe)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AUTH_SERVICE_URL}/internal/cases/{case_number}")
            return resp.status_code == 200
    except Exception as exc:
        logger.warning("Failed to check case %s: %s", case_number, exc)
    return False
