import shutil
import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Artifact

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_BASE = os.getenv("EVIDENCE_STORAGE_PATH", "/evidence-storage")

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
    # 1. Read gateway headers
    actor_id = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id_str = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    
    try:
        corr_id = uuid.UUID(corr_id_str)
    except ValueError:
        corr_id = uuid.uuid4()

    # 2. Generate new artifact ID
    artifact_id = uuid.uuid4()
    
    # 3. Stream file to shared volume
    artifact_dir = os.path.join(STORAGE_BASE, str(artifact_id))
    storage_path = os.path.join(artifact_dir, "original.bin")
    os.makedirs(artifact_dir, exist_ok=True)
    
    file_size = 0
    try:
        with open(storage_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
    except Exception as e:
        # Cleanup if streaming fails
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

    # 4. Initial DB Insert (PENDING)
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
            correlation_id=corr_id
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception as e:
        db.rollback()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to save initial artifact metadata: {str(e)}")

    # 5. gRPC Integrations
    from grpc_clients.hash_sign_client import compute_and_sign
    from grpc_clients.ledger_client import append_proof

    # Call Hash & Sign
    hs_success, hash_value, signature_value, hs_error = compute_and_sign(
        artifact_id=str(artifact_id),
        case_id=case_id,
        file_path=storage_path,
        file_name=file.filename,
        file_size=file_size,
        timeout=15
    )
    if not hs_success:
        db.delete(artifact)
        db.commit()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=503, detail=f"Hash & Sign failed: {hs_error}")

    # Call Ledger
    l_success, ledger_record_id, l_error = append_proof(
        artifact_id=str(artifact_id),
        case_id=case_id,
        hash_value=hash_value,
        signature_value=signature_value,
        timeout=15
    )
    if not l_success:
        db.delete(artifact)
        db.commit()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=503, detail=f"Ledger append failed: {l_error}")

    # 6. Finalize Artifact
    try:
        from datetime import datetime, timezone
        from db.models import OutboxEvent
        
        artifact.hash_value = hash_value
        artifact.signature_value = signature_value
        artifact.ledger_record_id = uuid.UUID(ledger_record_id)
        artifact.status = "INGESTED"
        
        # Outbox Pattern: Insert event in the SAME transaction
        event_id = str(uuid.uuid4())
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        
        envelope = {
            "event_id": event_id,
            "event_type": "EvidenceIngested",
            "routing_key": "forensicchain.evidence.ingested",
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
                "ledger_record_id": str(artifact.ledger_record_id)
            }
        }
        
        outbox_event = OutboxEvent(
            event_id=uuid.UUID(event_id),
            aggregate_id=str(artifact.artifact_id),
            event_type="EvidenceIngested",
            payload_json=envelope,
            status="PENDING"
        )
        db.add(outbox_event)
        
        db.commit()
        db.refresh(artifact)
    except Exception as e:
        db.rollback()
        db.delete(artifact)
        db.commit()
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to finalize artifact and outbox event: {str(e)}")

    # Return full response
    return {
        "artifact_id": str(artifact.artifact_id),
        "case_id": artifact.case_id,
        "file_name": artifact.file_name,
        "file_size": artifact.file_size,
        "hash_value": artifact.hash_value,
        "signature_value": artifact.signature_value,
        "ledger_record_id": str(artifact.ledger_record_id),
        "status": artifact.status,
        "uploaded_at": artifact.uploaded_at.isoformat() if artifact.uploaded_at else None
    }

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

    verification_id = uuid.uuid4()

    # FIX-A6: structured temp path under /evidence-storage/tmp/{artifact_id}/
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

        from grpc_clients.hash_sign_client import recompute_hash, verify_signature
        from grpc_clients.ledger_client import get_proof_by_artifact, validate_ledger_chain, append_verification_record

        # 1. Validate Ledger chain integrity
        lv_success, is_valid_chain, lv_error = validate_ledger_chain(timeout=15)
        if not lv_success:
            raise HTTPException(status_code=503, detail=f"Ledger validation check failed: {lv_error}")
        if not is_valid_chain:
            return {"status": "LEDGER_CORRUPTED", "message": "The immutable ledger chain is corrupted."}

        # 2. Get original proof
        gp_success, proof_data, gp_error = get_proof_by_artifact(artifact_id, timeout=15)
        if not gp_success:
            raise HTTPException(status_code=404, detail=f"Failed to fetch proof: {gp_error}")

        orig_hash = proof_data["hash_value"]
        orig_sig = proof_data["signature_value"]

        # 3. Verify cryptographic signature
        vs_success, is_sig_valid, vs_error = verify_signature(artifact_id, orig_hash, orig_sig, timeout=15)
        if not vs_success:
            raise HTTPException(status_code=503, detail=f"Signature verification failed: {vs_error}")
        if not is_sig_valid:
            _write_verification_outbox(
                db, artifact_id, actor_id, actor_role, corr_id,
                "VerificationFailed", "INVALID_SIGNATURE", orig_hash, orig_hash
            )
            return {"status": "INVALID_SIGNATURE", "message": "The cryptographic signature of the original hash is invalid."}

        # 4. Recompute hash of submitted file
        rh_success, current_hash, rh_error = recompute_hash(
            artifact_id=artifact_id,
            case_id="VERIFY",
            file_path=temp_path,
            file_name=file.filename,
            file_size=file_size,
            timeout=15
        )
        if not rh_success:
            raise HTTPException(status_code=503, detail=f"Hash recomputation failed: {rh_error}")

        # 5. Compare hashes — determine result
        if current_hash != orig_hash:
            _record_verification(
                artifact_id=artifact_id, case_id="VERIFY",
                verification_result="TAMPERED",
                original_hash=orig_hash, current_hash=current_hash,
                verified_by=actor_id
            )
            _write_verification_outbox(
                db, artifact_id, actor_id, actor_role, corr_id,
                "VerificationFailed", "TAMPERED", orig_hash, current_hash
            )
            return {"status": "TAMPERED", "message": "The artifact hash does not match the original ledger record."}

        # 6. FIX-A5: Append verification record to ledger
        _record_verification(
            artifact_id=artifact_id, case_id="VERIFY",
            verification_result="VALID",
            original_hash=orig_hash, current_hash=current_hash,
            verified_by=actor_id
        )
        _write_verification_outbox(
            db, artifact_id, actor_id, actor_role, corr_id,
            "VerificationPassed", "VALID", orig_hash, current_hash
        )

        return {"status": "VALID", "message": "The artifact is intact and cryptographically verified."}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass  # dir not empty or already gone — fine


def _record_verification(
    artifact_id: str, case_id: str,
    verification_result: str,
    original_hash: str, current_hash: str,
    verified_by: str
):
    from grpc_clients.ledger_client import append_verification_record
    vr_success, _, vr_error = append_verification_record(
        artifact_id=artifact_id,
        case_id=case_id,
        verification_result=verification_result,
        original_hash=original_hash,
        current_hash=current_hash,
        verified_by=verified_by,
        timeout=15
    )
    if not vr_success:
        logger.warning(f"AppendVerificationRecord failed for {artifact_id}: {vr_error}")


def _write_verification_outbox(
    db: Session,
    artifact_id: str,
    actor_id: str,
    actor_role: str,
    corr_id: uuid.UUID,
    event_type: str,
    verification_result: str,
    original_hash: str,
    current_hash: str,
):
    from datetime import datetime, timezone
    from db.models import OutboxEvent

    event_id = str(uuid.uuid4())
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    routing_key = f"forensicchain.evidence.{event_type.lower()}"

    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "routing_key": routing_key,
        "artifact_id": artifact_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timestamp_iso,
        "correlation_id": str(corr_id),
        "payload": {
            "verification_result": verification_result,
            "original_hash": original_hash,
            "current_hash": current_hash,
        }
    }
    try:
        outbox_event = OutboxEvent(
            event_id=uuid.UUID(event_id),
            aggregate_id=artifact_id,
            event_type=event_type,
            payload_json=envelope,
            status="PENDING"
        )
        db.add(outbox_event)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to write verification outbox event for {artifact_id}: {e}")

@router.get("/evidence/{artifact_id}")
async def get_evidence(
    artifact_id: str,
    db: Session = Depends(get_db)
):
    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    artifact = db.query(Artifact).filter(Artifact.artifact_id == artifact_uuid).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    from datetime import timezone
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
        "uploaded_at": uploaded_at.isoformat() if uploaded_at else None
    }


