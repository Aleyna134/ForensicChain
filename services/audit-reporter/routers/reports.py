import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aio_pika
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_client import get_artifact_case_id, get_assigned_case_numbers
from db.database import get_db
from db.models import Report
from db.repository import get_report, get_reports_by_artifact, insert_report
from rabbitmq.publisher import publish_event
from report_generator import build_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_identity(request: Request) -> tuple[str, str, str]:
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    return actor_id, actor_role, corr_id


def _get_exchange(request: Request) -> aio_pika.abc.AbstractExchange:
    return request.app.state.rabbitmq_exchange


class ReportOut(BaseModel):
    report_id: str
    artifact_id: str
    case_id: str | None
    report_hash: str
    format: str
    generated_at: str
    generated_by: str
    storage_path: str | None = None

    model_config = {"from_attributes": True}


class ReportVerifyOut(BaseModel):
    report_id: str
    report_valid: bool
    stored_hash: str
    current_hash: str
    verified_at: str


@router.post("/{artifact_id}", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def generate_report(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ReportOut:
    actor_id, actor_role, corr_id = _get_identity(request)
    ip_address = request.client.host if request.client else None

    case_id = await get_artifact_case_id(artifact_id)
    if not case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    assigned = await get_assigned_case_numbers(actor_id)
    if case_id not in assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not assigned to this case",
        )

    report_id = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc).isoformat()

    try:
        _, report_hash, storage_path = await build_report(
            report_id=report_id,
            artifact_id=artifact_id,
            generated_by=actor_id,
            generated_at=generated_at,
            actor_id=actor_id,
            actor_role=actor_role,
            corr_id=corr_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        candidate = Path(f"/report-storage/{report_id}.pdf")
        if candidate.exists():
            candidate.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Report generation failed: {exc}",
        )

    report = Report(
        report_id=report_id,
        artifact_id=artifact_id,
        case_id=case_id,
        generated_by=actor_id,
        generated_at=datetime.now(timezone.utc),
        format="PDF",
        report_hash=report_hash,
        storage_path=storage_path,
        correlation_id=corr_id,
    )
    insert_report(db, report)
    db.commit()
    db.refresh(report)

    await publish_event(
        _get_exchange(request),
        event_type="ReportGenerated",
        routing_key="forensicchain.report.generated",
        artifact_id=artifact_id,
        case_id=report.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        reason="Forensic audit report generated",
        payload={
            "report_id": report_id,
            "report_hash": report_hash,
            "report_format": "PDF",
            "ip_address": ip_address,
        },
    )

    return ReportOut(
        report_id=report.report_id,
        artifact_id=report.artifact_id,
        case_id=report.case_id,
        report_hash=report.report_hash,
        format=report.format,
        generated_at=report.generated_at.isoformat(),
        generated_by=report.generated_by,
        storage_path=report.storage_path,
    )


@router.get("/by-artifact/{artifact_id}", response_model=list[ReportOut])
async def list_reports_by_artifact(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    actor_id, _, _ = _get_identity(request)

    case_id = await get_artifact_case_id(artifact_id)
    if not case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    assigned = await get_assigned_case_numbers(actor_id)
    if case_id not in assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this case")

    reports = get_reports_by_artifact(db, artifact_id)
    return [
        ReportOut(
            report_id=r.report_id,
            artifact_id=r.artifact_id,
            case_id=r.case_id,
            report_hash=r.report_hash,
            format=r.format,
            generated_at=r.generated_at.isoformat(),
            generated_by=r.generated_by,
            storage_path=r.storage_path,
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportOut)
def get_report_metadata(
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportOut:
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return ReportOut(
        report_id=report.report_id,
        artifact_id=report.artifact_id,
        case_id=report.case_id,
        report_hash=report.report_hash,
        format=report.format,
        generated_at=report.generated_at.isoformat(),
        generated_by=report.generated_by,
        storage_path=report.storage_path,
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    actor_id, actor_role, corr_id = _get_identity(request)

    report = get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not report.storage_path or not Path(report.storage_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on storage",
        )

    pdf_bytes = Path(report.storage_path).read_bytes()

    await publish_event(
        _get_exchange(request),
        event_type="ReportDownloaded",
        routing_key="forensicchain.report.downloaded",
        artifact_id=report.artifact_id,
        case_id=report.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        reason="Report downloaded by user",
        payload={"ip_address": request.client.host if request.client else None},
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.pdf"'},
    )


@router.post("/{report_id}/verify", response_model=ReportVerifyOut)
async def verify_report(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ReportVerifyOut:
    actor_id, actor_role, corr_id = _get_identity(request)
    ip_address = request.client.host if request.client else None

    report = get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not report.storage_path or not Path(report.storage_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on storage",
        )

    current_hash = hashlib.sha256(Path(report.storage_path).read_bytes()).hexdigest()
    report_valid = current_hash == report.report_hash
    verified_at = datetime.now(timezone.utc).isoformat()

    await publish_event(
        _get_exchange(request),
        event_type="ReportVerified",
        routing_key="forensicchain.report.verified",
        artifact_id=report.artifact_id,
        case_id=report.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        reason="Report integrity verification",
        payload={
            "report_id": report_id,
            "report_valid": report_valid,
            "stored_hash": report.report_hash,
            "current_hash": current_hash,
            "ip_address": ip_address,
        },
    )

    return ReportVerifyOut(
        report_id=report_id,
        report_valid=report_valid,
        stored_hash=report.report_hash,
        current_hash=current_hash,
        verified_at=verified_at,
    )
