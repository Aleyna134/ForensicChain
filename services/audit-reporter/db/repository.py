from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Report


def insert_report(db: Session, report: Report) -> Report:
    db.add(report)
    db.flush()
    return report


def get_report(db: Session, report_id: str) -> Report | None:
    return db.get(Report, report_id)


def get_reports_by_artifact(db: Session, artifact_id: str) -> list[Report]:
    return list(
        db.execute(
            select(Report)
            .where(Report.artifact_id == artifact_id)
            .order_by(Report.generated_at.desc())
        ).scalars().all()
    )
