import shutil
import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Artifact, OutboxEvent
from grpc_clients.hash_sign_client import compute_and_sign_async, recompute_hash_async, verify_signature_async
from grpc_clients.ledger_client import (
    append_proof_async,
    get_proof_by_artifact_async,
    validate_ledger_chain_async,
    append_verification_record_async,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_BASE = os.getenv("EVIDENCE_STORAGE_PATH", "/evidence-storage")

_VERIFICATION_ROUTING_KEYS = {
    "VerificationRequested": "forensicchain.verification.requested",
    "VerificationPassed":    "forensicchain.verification.passed",
    "VerificationFailed":    "forensicchain.verification.failed",
}


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post("/evidence", status_code=201)
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    case_id: str = Form(...),
    title: str = Form(...),
    artifact_type: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id_str = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))

    try:
        corr_id = uuid.UUID(corr_id_str)
    except ValueError:
        corr_id = uuid.uuid4()

    artifact_id = uuid.uuid4()
    artifact_dir = os.path.join(STORAGE_BASE, str(artifact_id))
    storage_path = os.path.join(artifact_dir, "original.bin")
    os.makedirs(artifact_dir, exist_ok=True)

    file_size = 0
    try:
        with open(storage_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
    except Exception as e:
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

    try:
        artifact = Artifact(
            artifact_id=artifact_id,
            case_id=case_id,
            file_name=file.filename,
            file_size=file_size,
            artifact_type=artifact_type,
            storage_path=storage_path,
            description=description,
            uploaded_by=actor_id,
            status="PENDING",
            correlation_id=corr_id,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception as e:
        db.rollback()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to save initial artifact metadata: {str(e)}")

    hs_success, hash_value, hash_algorithm, signature_value, hs_error = await compute_and_sign_async(
        artifact_id=str(artifact_id),
        case_id=case_id,
        file_path=storage_path,
        file_name=file.filename,
        file_size=file_size,
        timeout=15,
    )
    if not hs_success:
        artifact.status = "INGESTION_FAILED"
        db.commit()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=503, detail=f"Hash & Sign failed: {hs_error}")

    l_success, ledger_record_id, l_error = await append_proof_async(
        artifact_id=str(artifact_id),
        case_id=case_id,
        hash_value=hash_value,
        signature_value=signature_value,
        timeout=15,
    )
    if not l_success:
        artifact.status = "INGESTION_FAILED"
        db.commit()
        raise HTTPException(status_code=503, detail=f"Ledger append failed: {l_error}")

    try:
        artifact.hash_value = hash_value
        artifact.hash_algorithm = hash_algorithm
        artifact.signature_value = signature_value
        artifact.ledger_record_id = uuid.UUID(ledger_record_id)
        artifact.status = "INGESTED"

        event_id = str(uuid.uuid4())
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        routing_key = "forensicchain.evidence.ingested"

        envelope = {
            "event_id": event_id,
            "event_type": "EvidenceIngested",
            "routing_key": routing_key,
            "artifact_id": str(artifact.artifact_id),
            "case_id": artifact.case_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "timestamp": timestamp_iso,
            "correlation_id": str(corr_id),
            "reason": "Initial evidence ingestion",
            "payload": {
                "file_name": artifact.file_name,
                "file_size": artifact.file_size,
                "artifact_type": artifact.artifact_type,
                "hash_algorithm": artifact.hash_algorithm,
                "hash_value": artifact.hash_value,
                "ledger_record_id": str(artifact.ledger_record_id),
            },
        }

        outbox_event = OutboxEvent(
            event_id=uuid.UUID(event_id),
            event_type="EvidenceIngested",
            routing_key=routing_key,
            payload=envelope,
            published=False,
        )
        db.add(outbox_event)
        db.commit()
        db.refresh(artifact)
    except Exception as e:
        db.rollback()
        artifact.status = "INGESTION_FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to finalize artifact and outbox event: {str(e)}")

    return {
        "artifact_id": str(artifact.artifact_id),
        "case_id": artifact.case_id,
        "file_name": artifact.file_name,
        "file_size": artifact.file_size,
        "hash_value": artifact.hash_value,
        "hash_algorithm": artifact.hash_algorithm,
        "signature_value": artifact.signature_value,
        "ledger_record_id": str(artifact.ledger_record_id),
        "status": artifact.status,
        "uploaded_at": artifact.uploaded_at.isoformat() if artifact.uploaded_at else None,
    }


# ── Verify ─────────────────────────────────────────────────────────────────────

@router.post("/evidence/{artifact_id}/verify", status_code=200)
async def verify_evidence(
    request: Request,
    artifact_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id_str = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    try:
        corr_id = uuid.UUID(corr_id_str)
    except ValueError:
        corr_id = uuid.uuid4()

    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    artifact = db.query(Artifact).filter(Artifact.artifact_id == artifact_uuid).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Spec §7: publish VerificationRequested before executing the verification flow
    _write_evidence_event_outbox(
        db=db,
        artifact_id=artifact_id,
        case_id=artifact.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        event_type="VerificationRequested",
        routing_key=_VERIFICATION_ROUTING_KEYS["VerificationRequested"],
        reason="Integrity verification requested",
    )

    verification_id = uuid.uuid4()
    verified_at = datetime.now(timezone.utc).isoformat()

    temp_dir = os.path.join(STORAGE_BASE, "tmp", artifact_id)
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{verification_id}.bin")

    file_size = 0
    try:
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)

        # Step 1: Recompute hash of submitted file
        rh_success, current_hash, rh_error = await recompute_hash_async(
            artifact_id=artifact_id,
            case_id="VERIFY",
            file_path=temp_path,
            file_name=file.filename,
            file_size=file_size,
            timeout=15,
        )
        if not rh_success:
            raise HTTPException(status_code=503, detail=f"Hash recomputation failed: {rh_error}")

        # Step 2: Get original proof from ledger
        gp_success, proof_data, gp_error = await get_proof_by_artifact_async(artifact_id, timeout=15)
        if not gp_success:
            raise HTTPException(status_code=404, detail=f"Failed to fetch proof: {gp_error}")

        orig_hash = proof_data["hash_value"]
        orig_sig = proof_data["signature_value"]

        # Step 3: Verify cryptographic signature on original hash
        vs_success, is_sig_valid, vs_error = await verify_signature_async(artifact_id, orig_hash, orig_sig, timeout=15)
        if not vs_success:
            raise HTTPException(status_code=503, detail=f"Signature verification failed: {vs_error}")

        # Step 4: Validate full ledger chain integrity
        lv_success, is_valid_chain, lv_error = await validate_ledger_chain_async(timeout=15)
        if not lv_success:
            raise HTTPException(status_code=503, detail=f"Ledger validation check failed: {lv_error}")

        # Step 5: Determine result — most severe condition wins
        if not is_valid_chain:
            verification_result = "LEDGER_CORRUPTED"
        elif not is_sig_valid:
            verification_result = "INVALID_SIGNATURE"
        elif current_hash != orig_hash:
            verification_result = "TAMPERED"
        else:
            verification_result = "VALID"

        # Step 6: Append VerificationRecord to ledger (best-effort)
        ver_record_id = await _record_verification(
            artifact_id=artifact_id,
            case_id=artifact.case_id,
            verification_result=verification_result,
            original_hash=orig_hash,
            current_hash=current_hash,
            verified_by=actor_id,
        )

        # Step 7: Publish VerificationPassed or VerificationFailed
        event_type = "VerificationPassed" if verification_result == "VALID" else "VerificationFailed"
        _write_verification_outbox(
            db=db,
            artifact_id=artifact_id,
            case_id=artifact.case_id,
            actor_id=actor_id,
            actor_role=actor_role,
            corr_id=corr_id,
            event_type=event_type,
            verification_result=verification_result,
            original_hash=orig_hash,
            current_hash=current_hash,
            ledger_record_id=ver_record_id,
        )

        return {
            "artifact_id": artifact_id,
            "verification_result": verification_result,
            "original_hash": orig_hash,
            "current_hash": current_hash,
            "signature_valid": is_sig_valid,
            "ledger_chain_valid": is_valid_chain,
            "verified_at": verified_at,
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


# ── Get metadata ───────────────────────────────────────────────────────────────

@router.get("/evidence/{artifact_id}")
async def get_evidence(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id_str = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    ip_address = request.client.host if request.client else None

    try:
        corr_id = uuid.UUID(corr_id_str)
    except ValueError:
        corr_id = uuid.uuid4()

    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    artifact = db.query(Artifact).filter(Artifact.artifact_id == artifact_uuid).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    _write_evidence_event_outbox(
        db=db,
        artifact_id=artifact_id,
        case_id=artifact.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        event_type="EvidenceViewed",
        routing_key="forensicchain.evidence.viewed",
        reason="Evidence metadata accessed",
        ip_address=ip_address,
    )

    uploaded_at = artifact.uploaded_at
    if uploaded_at and uploaded_at.tzinfo is None:
        uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)

    return {
        "artifact_id": str(artifact.artifact_id),
        "case_id": artifact.case_id,
        "file_name": artifact.file_name,
        "file_size": artifact.file_size,
        "artifact_type": artifact.artifact_type,
        "description": artifact.description,
        "hash_algorithm": artifact.hash_algorithm,
        "hash_value": artifact.hash_value,
        "signature_value": artifact.signature_value,
        "ledger_record_id": str(artifact.ledger_record_id) if artifact.ledger_record_id else None,
        "status": artifact.status,
        "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
    }


# ── Download binary ────────────────────────────────────────────────────────────

@router.get("/evidence/{artifact_id}/download")
async def download_evidence(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id_str = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    ip_address = request.client.host if request.client else None

    try:
        corr_id = uuid.UUID(corr_id_str)
    except ValueError:
        corr_id = uuid.uuid4()

    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    artifact = db.query(Artifact).filter(Artifact.artifact_id == artifact_uuid).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if not artifact.storage_path or not os.path.exists(artifact.storage_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on storage")

    _write_evidence_event_outbox(
        db=db,
        artifact_id=artifact_id,
        case_id=artifact.case_id,
        actor_id=actor_id,
        actor_role=actor_role,
        corr_id=corr_id,
        event_type="EvidenceDownloaded",
        routing_key="forensicchain.evidence.downloaded",
        reason="Evidence file downloaded",
        ip_address=ip_address,
    )

    return FileResponse(
        path=artifact.storage_path,
        media_type="application/octet-stream",
        filename=artifact.file_name,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _record_verification(
    artifact_id: str,
    case_id: str,
    verification_result: str,
    original_hash: str,
    current_hash: str,
    verified_by: str,
) -> str:
    vr_success, record_id, vr_error = await append_verification_record_async(
        artifact_id=artifact_id,
        case_id=case_id,
        verification_result=verification_result,
        original_hash=original_hash,
        current_hash=current_hash,
        verified_by=verified_by,
        timeout=15,
    )
    if not vr_success:
        logger.warning("AppendVerificationRecord failed for %s: %s", artifact_id, vr_error)
        return ""
    return record_id


def _write_verification_outbox(
    db: Session,
    artifact_id: str,
    case_id: str | None,
    actor_id: str,
    actor_role: str,
    corr_id: uuid.UUID,
    event_type: str,
    verification_result: str,
    original_hash: str,
    current_hash: str,
    ledger_record_id: str = "",
) -> None:
    event_id = str(uuid.uuid4())
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    routing_key = _VERIFICATION_ROUTING_KEYS[event_type]
    reason = (
        "Artifact integrity verified — result: VALID"
        if event_type == "VerificationPassed"
        else f"Artifact integrity verified — result: {verification_result}"
    )

    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "routing_key": routing_key,
        "artifact_id": artifact_id,
        "case_id": case_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timestamp_iso,
        "correlation_id": str(corr_id),
        "reason": reason,
        "payload": {
            "verification_result": verification_result,
            "original_hash": original_hash,
            "current_hash": current_hash,
            "ledger_record_id": ledger_record_id,
        },
    }
    try:
        outbox_event = OutboxEvent(
            event_id=uuid.UUID(event_id),
            event_type=event_type,
            routing_key=routing_key,
            payload=envelope,
            published=False,
        )
        db.add(outbox_event)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Failed to write %s outbox event for %s: %s", event_type, artifact_id, e)


def _write_evidence_event_outbox(
    db: Session,
    artifact_id: str,
    case_id: str | None,
    actor_id: str,
    actor_role: str,
    corr_id: uuid.UUID,
    event_type: str,
    routing_key: str,
    reason: str = "",
    ip_address: str | None = None,
) -> None:
    event_id = str(uuid.uuid4())
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "routing_key": routing_key,
        "artifact_id": artifact_id,
        "case_id": case_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timestamp_iso,
        "correlation_id": str(corr_id),
        "reason": reason,
        "payload": {"ip_address": ip_address},
    }
    try:
        outbox_event = OutboxEvent(
            event_id=uuid.UUID(event_id),
            event_type=event_type,
            routing_key=routing_key,
            payload=envelope,
            published=False,
        )
        db.add(outbox_event)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Failed to write %s outbox event for %s: %s", event_type, artifact_id, e)
