from datetime import datetime

from sqlalchemy import Index, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    case_id: Mapped[str | None] = mapped_column(String(64))
    generated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="PDF")
    report_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))

    __table_args__ = (
        Index("idx_reports_artifact", "artifact_id", "generated_at"),
    )
