from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CustodyEvent, ProcessedEventId


async def is_already_processed(db: AsyncSession, event_id: str) -> bool:
    return await db.get(ProcessedEventId, event_id) is not None


async def get_last_event_hash(db: AsyncSession, artifact_id: str) -> str | None:
    result = await db.scalars(
        select(CustodyEvent)
        .where(CustodyEvent.artifact_id == artifact_id)
        .order_by(CustodyEvent.timestamp.desc(), CustodyEvent.id.desc())
        .limit(1)
    )
    row = result.first()
    return row.event_hash if row else None


async def insert_custody_event(
    db: AsyncSession,
    *,
    event_id: str,
    artifact_id: str,
    case_id: str | None,
    actor_id: str,
    actor_role: str,
    event_type: str,
    timestamp: datetime,
    reason: str | None,
    ip_address: str | None,
    correlation_id: str | None,
    payload: dict,
    previous_event_hash: str | None,
    event_hash: str,
) -> CustodyEvent:
    event = CustodyEvent(
        event_id=event_id,
        artifact_id=artifact_id,
        case_id=case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        event_type=event_type,
        timestamp=timestamp,
        reason=reason,
        ip_address=ip_address,
        correlation_id=correlation_id,
        payload=payload,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(event)
    return event


async def mark_processed(db: AsyncSession, event_id: str) -> None:
    db.add(ProcessedEventId(event_id=event_id))


async def get_timeline(db: AsyncSession, artifact_id: str) -> list[CustodyEvent]:
    result = await db.scalars(
        select(CustodyEvent)
        .where(CustodyEvent.artifact_id == artifact_id)
        .order_by(CustodyEvent.timestamp.asc(), CustodyEvent.id.asc())
    )
    return list(result.all())
