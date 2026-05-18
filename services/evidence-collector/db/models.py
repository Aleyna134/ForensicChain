import uuid
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .database import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(64), nullable=False)
    file_name = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    artifact_type = Column(String(64), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)

    uploaded_by = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    status = Column(String(32), nullable=False, default='PENDING')
    # status: PENDING | INGESTED | INGESTION_FAILED

    hash_value = Column(String(256), nullable=True)
    hash_algorithm = Column(String(32), nullable=True)
    signature_value = Column(Text, nullable=True)
    ledger_record_id = Column(UUID(as_uuid=True), nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index('idx_outbox_unpublished', 'published', 'created_at',
              postgresql_where=sa_text('published = FALSE')),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    event_type = Column(String(128), nullable=False)
    routing_key = Column(String(256), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
