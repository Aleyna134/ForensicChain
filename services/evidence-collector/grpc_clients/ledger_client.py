import os
import grpc
from datetime import datetime, timezone
from typing import Tuple
from . import ledger_pb2
from . import ledger_pb2_grpc

LEDGER_HOST = os.getenv("LEDGER_GRPC_HOST", "localhost")
LEDGER_PORT = os.getenv("LEDGER_GRPC_PORT", "50052")
CHANNEL_ADDRESS = f"{LEDGER_HOST}:{LEDGER_PORT}"

def append_proof(artifact_id: str, case_id: str, hash_value: str, signature_value: str, timeout: int = 15) -> Tuple[bool, str, str]:
    """
    Calls the Immutable Ledger Service synchronously to append an EVIDENCE_PROOF_CREATED record.
    Returns: (success, record_id, error_message)
    """
    try:
        with grpc.insecure_channel(CHANNEL_ADDRESS) as channel:
            stub = ledger_pb2_grpc.LedgerServiceStub(channel)
            request = ledger_pb2.ProofRecordRequest(
                artifact_id=artifact_id,
                case_id=case_id,
                record_type="EVIDENCE_PROOF_CREATED",
                hash_algorithm="SHA-256",
                hash_value=hash_value,
                signature_algorithm="RSA-SHA256",
                signature_value=signature_value,
                signer_id="hash-sign-service",
                created_at=datetime.now(timezone.utc).isoformat()
            )
            # Apply explicit timeout deadline
            response = stub.AppendProofRecord(request, timeout=timeout)
            
            if response.success:
                return True, response.record_id, ""
            else:
                return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal Error: {str(e)}"
