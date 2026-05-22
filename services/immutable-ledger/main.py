import asyncio
import logging
import grpc
from fastapi import Depends, FastAPI, HTTPException, Request
import uvicorn
import ledger_pb2_grpc
from servicer import LedgerServicer
from db.database import Base, engine, SessionLocal
from db.models import LedgerRecord, LedgerState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create DB schemas — ledger_state rows are created on first write per case
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Immutable Ledger REST API")
servicer_instance = LedgerServicer()

_LEDGER_VIEWER_ROLES = {"legal_reviewer", "admin"}


def _require_ledger_viewer(request: Request):
    role = request.headers.get("X-User-Role", "")
    if role not in _LEDGER_VIEWER_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: insufficient role")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "immutable-ledger"}

# Lightweight REST wrapper around gRPC logic for Audit Reporter
@app.get("/ledger/artifacts/{artifactId}")
def get_proof_by_artifact(artifactId: str):
    import ledger_pb2
    req = ledger_pb2.ArtifactProofRequest(artifact_id=artifactId)
    resp = servicer_instance.GetProofByArtifactId(req, None)
    if not resp.success:
        raise HTTPException(status_code=404, detail=resp.error_message)
    
    return {
        "record_id": resp.record_id,
        "artifact_id": resp.artifact_id,
        "case_id": resp.case_id,
        "hash_algorithm": resp.hash_algorithm,
        "hash_value": resp.hash_value,
        "signature_algorithm": resp.signature_algorithm,
        "signature_value": resp.signature_value,
        "signer_id": resp.signer_id,
        "record_hash": resp.record_hash
    }

@app.get("/ledger/records/{case_id}")
def get_ledger_records(case_id: str, request: Request, _: None = Depends(_require_ledger_viewer)):
    with SessionLocal() as db:
        records = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.case_id == case_id)
            .order_by(LedgerRecord.created_at.asc())
            .all()
        )
        return [
            {
                "record_id": str(r.record_id),
                "artifact_id": str(r.artifact_id),
                "case_id": r.case_id,
                "record_type": r.record_type,
                "hash_algorithm": r.hash_algorithm,
                "hash_value": r.hash_value,
                "payload_hash": r.payload_hash,
                "previous_record_hash": r.previous_record_hash,
                "record_hash": r.record_hash,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]


@app.get("/ledger/validate/{case_id}")
def validate_ledger(case_id: str, request: Request, _: None = Depends(_require_ledger_viewer)):
    import ledger_pb2
    req = ledger_pb2.ValidateLedgerRequest(case_id=case_id)
    resp = servicer_instance.ValidateLedgerChain(req, None)

    return {
        "case_id": case_id,
        "chain_valid": resp.chain_valid,
        "checked_records": resp.checked_records,
        "error_message": resp.error_message,
    }

async def serve_grpc():
    server = grpc.aio.server()
    ledger_pb2_grpc.add_LedgerServiceServicer_to_server(servicer_instance, server)
    server.add_insecure_port("[::]:50052")
    logger.info("Starting gRPC server on port 50052...")
    await server.start()
    await server.wait_for_termination()

async def main():
    grpc_task = asyncio.create_task(serve_grpc())
    
    # Run FastAPI server on port 8003
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8003, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info("Starting FastAPI server on port 8003...")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
