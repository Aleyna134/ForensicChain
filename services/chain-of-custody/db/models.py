from datetime import datetime

from sqlalchemy import BigInteger, Index, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, unique=True)
    artifact_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    case_id: Mapped[str | None] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    previous_event_hash: Mapped[str | None] = mapped_column(String(256))
    event_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_custody_artifact", "artifact_id", "timestamp"),
    )


class ProcessedEventId(Base):
    __tablename__ = "processed_event_ids"

    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
