import shutil
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Artifact

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

    # 4. Insert into DB (ONLY occurs after file is completely written)
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
            # Hash, signature, and ledger info are purposely left NULL here.
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception as e:
        db.rollback()
        # If DB insert fails, cleanup file and directory
        if os.path.exists(artifact_dir):
            shutil.rmtree(artifact_dir)
        raise HTTPException(status_code=500, detail=f"Failed to save artifact metadata: {str(e)}")

    # Return skeleton response (hash/ledger fields empty for now)
    return {
        "artifact_id": str(artifact.artifact_id),
        "case_id": artifact.case_id,
        "file_name": artifact.file_name,
        "file_size": artifact.file_size,
        "status": artifact.status,
        "uploaded_at": artifact.uploaded_at.isoformat() if artifact.uploaded_at else None
    }
