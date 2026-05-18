from sqlalchemy.orm import Session

from db.models import Report


def insert_report(db: Session, report: Report) -> Report:
    db.add(report)
    db.flush()
    return report


def get_report(db: Session, report_id: str) -> Report | None:
    return db.get(Report, report_id)
