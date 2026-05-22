import asyncio
import os
from typing import Tuple

import grpc

import ledger_pb2
import ledger_pb2_grpc

LEDGER_HOST = os.getenv("LEDGER_GRPC_HOST", "localhost")
LEDGER_PORT = os.getenv("LEDGER_GRPC_PORT", "50052")

_channel = grpc.insecure_channel(f"{LEDGER_HOST}:{LEDGER_PORT}")
_stub = ledger_pb2_grpc.LedgerServiceStub(_channel)


def append_report_proof(
    report_id: str,
    case_id: str,
    report_hash: str,
    generated_by: str,
    generated_at: str,
    timeout: int = 15,
) -> Tuple[bool, str, str]:
    """Anchor a report's SHA-256 hash in the immutable ledger.

    Returns: (success, record_id, error_message)
    """
    try:
        request = ledger_pb2.ProofRecordRequest(
            artifact_id=report_id,
            case_id=case_id or "",
            record_type="REPORT_PROOF_CREATED",
            hash_algorithm="SHA-256",
            hash_value=report_hash,
            signature_algorithm="",
            signature_value="",
            signer_id=generated_by,
            created_at=generated_at,
        )
        response = _stub.AppendProofRecord(request, timeout=timeout)
        if response.success:
            return True, response.record_id, ""
        return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal error: {str(e)}"


async def append_report_proof_async(
    report_id: str,
    case_id: str,
    report_hash: str,
    generated_by: str,
    generated_at: str,
    timeout: int = 15,
) -> Tuple[bool, str, str]:
    return await asyncio.to_thread(
        append_report_proof,
        report_id, case_id, report_hash, generated_by, generated_at, timeout,
    )
