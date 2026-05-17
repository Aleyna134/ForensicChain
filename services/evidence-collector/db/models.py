import uuid
from sqlalchemy import Column, String, BigInteger, Text, DateTime, func
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
    
    # Hash, signature, and ledger info (populated later)
    hash_value = Column(String(256), nullable=True)
    hash_algorithm = Column(String(32), nullable=True)
    signature_value = Column(Text, nullable=True)
    ledger_record_id = Column(UUID(as_uuid=True), nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    aggregate_id = Column(String(128), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload_json = Column(JSONB, nullable=False)
    status = Column(String(32), nullable=False, default='PENDING') # PENDING, PUBLISHED, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    retry_count = Column(BigInteger, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_error = Column(Text, nullable=True)
