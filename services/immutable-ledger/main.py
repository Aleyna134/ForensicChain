import asyncio
import logging
import grpc
from fastapi import FastAPI, HTTPException
import uvicorn
import ledger_pb2_grpc
from servicer import LedgerServicer
from db.database import Base, engine, SessionLocal
from db.models import LedgerRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create DB schemas
Base.metadata.create_all(bind=engine)
# Initialize ledger state if not exists
with SessionLocal() as db:
    from sqlalchemy import text
    try:
        db.execute(text("INSERT INTO ledger_state (id, last_record_hash) VALUES (1, NULL) ON CONFLICT (id) DO NOTHING"))
        db.commit()
    except Exception as e:
        logger.warning(f"Could not initialize ledger_state, possibly already initialized: {e}")
        db.rollback()

app = FastAPI(title="Immutable Ledger REST API")
servicer_instance = LedgerServicer()

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

@app.get("/ledger/validate")
def validate_ledger():
    import ledger_pb2
    req = ledger_pb2.ValidateLedgerRequest(full_validation=True)
    resp = servicer_instance.ValidateLedgerChain(req, None)
    
    return {
        "chain_valid": resp.chain_valid,
        "checked_records": resp.checked_records,
        "error_message": resp.error_message
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
