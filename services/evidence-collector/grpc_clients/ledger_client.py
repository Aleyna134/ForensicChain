import asyncio
import os
import grpc
from datetime import datetime, timezone
from typing import Tuple
from . import ledger_pb2
from . import ledger_pb2_grpc

LEDGER_HOST = os.getenv("LEDGER_GRPC_HOST", "localhost")
LEDGER_PORT = os.getenv("LEDGER_GRPC_PORT", "50052")
CHANNEL_ADDRESS = f"{LEDGER_HOST}:{LEDGER_PORT}"

# Singleton channel — avoids a TCP handshake on every RPC call (Risk 2 fix).
_channel = grpc.insecure_channel(CHANNEL_ADDRESS)
_stub = ledger_pb2_grpc.LedgerServiceStub(_channel)


def append_proof(
    artifact_id: str, case_id: str, hash_value: str,
    signature_value: str, timeout: int = 15,
) -> Tuple[bool, str, str]:
    """Returns: (success, record_id, error_message)"""
    try:
        request = ledger_pb2.ProofRecordRequest(
            artifact_id=artifact_id,
            case_id=case_id,
            record_type="EVIDENCE_PROOF_CREATED",
            hash_algorithm="SHA-256",
            hash_value=hash_value,
            signature_algorithm="RSA-SHA256",
            signature_value=signature_value,
            signer_id="hash-sign-service",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        response = _stub.AppendProofRecord(request, timeout=timeout)
        if response.success:
            return True, response.record_id, ""
        return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal Error: {str(e)}"


async def append_proof_async(
    artifact_id: str, case_id: str, hash_value: str,
    signature_value: str, timeout: int = 15,
) -> Tuple[bool, str, str]:
    """Non-blocking wrapper — runs sync gRPC call in thread pool (Risk 3 fix)."""
    return await asyncio.to_thread(append_proof, artifact_id, case_id, hash_value, signature_value, timeout)


def get_proof_by_artifact(artifact_id: str, timeout: int = 15) -> Tuple[bool, dict, str]:
    """Returns: (success, proof_data_dict, error_message)"""
    try:
        request = ledger_pb2.ArtifactProofRequest(artifact_id=artifact_id)
        response = _stub.GetProofByArtifactId(request, timeout=timeout)
        if response.success:
            return True, {
                "hash_value": response.hash_value,
                "signature_value": response.signature_value,
                "record_id": response.record_id,
            }, ""
        return False, {}, response.error_message
    except grpc.RpcError as e:
        return False, {}, f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, {}, f"Internal Error: {str(e)}"


async def get_proof_by_artifact_async(artifact_id: str, timeout: int = 15) -> Tuple[bool, dict, str]:
    return await asyncio.to_thread(get_proof_by_artifact, artifact_id, timeout)


def append_verification_record(
    artifact_id: str, case_id: str, verification_result: str,
    original_hash: str, current_hash: str, verified_by: str, timeout: int = 15,
) -> Tuple[bool, str, str]:
    """Returns: (success, record_id, error_message)"""
    try:
        request = ledger_pb2.VerificationRecordRequest(
            artifact_id=artifact_id,
            case_id=case_id,
            record_type="VERIFICATION_RESULT_RECORDED",
            verification_result=verification_result,
            original_hash=original_hash,
            current_hash=current_hash,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc).isoformat(),
        )
        response = _stub.AppendVerificationRecord(request, timeout=timeout)
        if response.success:
            return True, response.record_id, ""
        return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal Error: {str(e)}"


async def append_verification_record_async(
    artifact_id: str, case_id: str, verification_result: str,
    original_hash: str, current_hash: str, verified_by: str, timeout: int = 15,
) -> Tuple[bool, str, str]:
    return await asyncio.to_thread(
        append_verification_record,
        artifact_id, case_id, verification_result,
        original_hash, current_hash, verified_by, timeout,
    )


def validate_ledger_chain(timeout: int = 30) -> Tuple[bool, bool, str]:
    """Returns: (success, is_valid, error_message)"""
    try:
        request = ledger_pb2.ValidateLedgerRequest(full_validation=True)
        response = _stub.ValidateLedgerChain(request, timeout=timeout)
        return True, response.chain_valid, response.error_message
    except grpc.RpcError as e:
        return False, False, f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, False, f"Internal Error: {str(e)}"


async def validate_ledger_chain_async(timeout: int = 30) -> Tuple[bool, bool, str]:
    return await asyncio.to_thread(validate_ledger_chain, timeout)
