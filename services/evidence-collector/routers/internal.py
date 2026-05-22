import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Artifact

# Auth validation has moved to auth-service (services/auth-service).
# This router serves only internal service-to-service calls that bypass nginx.
router = APIRouter(prefix="/internal")


@router.get("/artifacts/{artifact_id}/case")
def get_artifact_case(artifact_id: str, db: Session = Depends(get_db)):
    """Returns the case_id for an artifact. Called by custody-service and audit-reporter."""
    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact ID")

    artifact = db.query(Artifact).filter(Artifact.artifact_id == artifact_uuid).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    return {"case_id": artifact.case_id}
