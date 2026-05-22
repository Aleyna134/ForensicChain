import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from clients import custody_client, evidence_client, ledger_client
from grpc_clients.ledger_write_client import append_report_proof_async

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STORAGE_PATH: str = os.environ.get("REPORT_STORAGE_PATH", "/report-storage")

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _filesizeformat(value: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


_jinja_env.filters["filesizeformat"] = _filesizeformat


async def build_report(
    *,
    report_id: str,
    artifact_id: str,
    generated_by: str,
    generated_at: str,
    actor_id: str,
    actor_role: str,
    corr_id: str,
) -> tuple[bytes, str, str]:
    """
    Pull data from all three upstream services, render a PDF report,
    compute its SHA-256 hash, and persist it to the shared volume.

    Returns (pdf_bytes, report_hash, storage_path).
    Raises HTTPException (503) if any upstream service is unreachable.
    """
    artifact: dict[str, Any] = await evidence_client.get_artifact(
        artifact_id, actor_id=actor_id, actor_role=actor_role, corr_id=corr_id
    )
    ledger: dict[str, Any] = await ledger_client.get_proof(
        artifact_id, actor_id=actor_id, actor_role=actor_role, corr_id=corr_id
    )
    timeline: dict[str, Any] = await custody_client.get_timeline(
        artifact_id, actor_id=actor_id, actor_role=actor_role, corr_id=corr_id
    )

    if "file_size" in artifact:
        artifact["file_size"] = int(artifact["file_size"])

    html_content = _jinja_env.get_template("report.html").render(
        report_id=report_id,
        generated_by=generated_by,
        generated_at=generated_at,
        artifact=artifact,
        ledger=ledger,
        timeline=timeline,
    )

    pdf_bytes: bytes = HTML(string=html_content).write_pdf()
    report_hash: str = hashlib.sha256(pdf_bytes).hexdigest()

    storage_path = Path(_STORAGE_PATH) / f"{report_id}.pdf"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(pdf_bytes)

    # Anchor the report's SHA-256 hash in the immutable ledger (best-effort).
    # Failure does not block report delivery — the report_db hash still provides
    # local tamper detection; the ledger entry anchors the report hash in the
    # case-level ledger chain.
    case_id: str = artifact.get("case_id") or ""
    success, ledger_record_id, err = await append_report_proof_async(
        report_id=report_id,
        case_id=case_id,
        report_hash=report_hash,
        generated_by=generated_by,
        generated_at=generated_at,
    )
    if not success:
        logger.warning("Could not anchor report %s in ledger: %s", report_id, err)
    else:
        logger.info("Report %s anchored in ledger as record %s", report_id, ledger_record_id)

    return pdf_bytes, report_hash, str(storage_path)
