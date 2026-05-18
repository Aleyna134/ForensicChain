import uuid
from sqlalchemy import Column, String, Integer, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .database import Base

class LedgerRecord(Base):
    __tablename__ = "ledger_records"

    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(String(64), nullable=False)
    record_type = Column(String(64), nullable=False)
    
    hash_algorithm = Column(String(32))
    hash_value = Column(String(256))
    signature_algorithm = Column(String(32))
    signature_value = Column(Text)
    signer_id = Column(String(128))
    
    payload_hash = Column(String(256), nullable=False)
    previous_record_hash = Column(String(256), nullable=True)
    record_hash = Column(String(256), nullable=False)
    
    raw_payload = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class LedgerState(Base):
    __tablename__ = "ledger_state"

    id = Column(Integer, primary_key=True, default=1)
    last_record_hash = Column(String(256), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
