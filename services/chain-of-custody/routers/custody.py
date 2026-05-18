from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import CustodyEvent
from db.repository import get_timeline

router = APIRouter(prefix="/custody", tags=["custody"])


class CustodyEventOut(BaseModel):
    event_id: str
    event_type: str
    actor_id: str
    actor_role: str
    timestamp: datetime
    reason: str | None
    ip_address: str | None
    event_hash: str
    previous_event_hash: str | None

    model_config = {
        "from_attributes": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }


class TimelineResponse(BaseModel):
    artifact_id: str
    total_events: int
    chain_valid: bool
    events: list[CustodyEventOut]


def _validate_chain(events: list[CustodyEvent]) -> bool:
    for i, event in enumerate(events):
        expected_prev = events[i - 1].event_hash if i > 0 else None
        if event.previous_event_hash != expected_prev:
            return False
    return True


@router.get("/{artifact_id}/timeline", response_model=TimelineResponse)
async def get_custody_timeline(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    events = await get_timeline(db, str(artifact_id))

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No custody events found for artifact {artifact_id}",
        )

    chain_valid = _validate_chain(events)

    return TimelineResponse(
        artifact_id=str(artifact_id),
        total_events=len(events),
        chain_valid=chain_valid,
        events=[CustodyEventOut.model_validate(e) for e in events],
    )
