import asyncio
import os
import grpc
from typing import Tuple
from . import hash_sign_pb2
from . import hash_sign_pb2_grpc

HASH_SIGN_HOST = os.getenv("HASH_SIGN_GRPC_HOST", "localhost")
HASH_SIGN_PORT = os.getenv("HASH_SIGN_GRPC_PORT", "50051")
CHANNEL_ADDRESS = f"{HASH_SIGN_HOST}:{HASH_SIGN_PORT}"

# Singleton channel — avoids a TCP handshake on every RPC call (Risk 2 fix).
_channel = grpc.insecure_channel(CHANNEL_ADDRESS)
_stub = hash_sign_pb2_grpc.HashSignServiceStub(_channel)


def compute_and_sign(
    artifact_id: str, case_id: str, file_path: str,
    file_name: str, file_size: int, timeout: int = 15,
) -> Tuple[bool, str, str, str, str]:
    """Returns: (success, hash_value, hash_algorithm, signature_value, error_message)"""
    try:
        request = hash_sign_pb2.ArtifactHashRequest(
            artifact_id=artifact_id,
            case_id=case_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            hash_algorithm="SHA-256",
        )
        response = _stub.ComputeAndSignHash(request, timeout=timeout)
        if response.success:
            return True, response.hash_value, response.hash_algorithm, response.signature_value, ""
        return False, "", "", "", response.error_message
    except grpc.RpcError as e:
        return False, "", "", "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", "", "", f"Internal Error: {str(e)}"


async def compute_and_sign_async(
    artifact_id: str, case_id: str, file_path: str,
    file_name: str, file_size: int, timeout: int = 15,
) -> Tuple[bool, str, str, str, str]:
    """Non-blocking wrapper — runs sync gRPC call in thread pool (Risk 3 fix)."""
    return await asyncio.to_thread(
        compute_and_sign, artifact_id, case_id, file_path, file_name, file_size, timeout
    )


def recompute_hash(
    artifact_id: str, case_id: str, file_path: str,
    file_name: str, file_size: int, timeout: int = 15,
) -> Tuple[bool, str, str]:
    """Returns: (success, hash_value, error_message)"""
    try:
        request = hash_sign_pb2.ArtifactHashRequest(
            artifact_id=artifact_id,
            case_id=case_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            hash_algorithm="SHA-256",
        )
        response = _stub.RecomputeHash(request, timeout=timeout)
        if response.success:
            return True, response.hash_value, ""
        return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal Error: {str(e)}"


async def recompute_hash_async(
    artifact_id: str, case_id: str, file_path: str,
    file_name: str, file_size: int, timeout: int = 15,
) -> Tuple[bool, str, str]:
    return await asyncio.to_thread(
        recompute_hash, artifact_id, case_id, file_path, file_name, file_size, timeout
    )


def verify_signature(
    artifact_id: str, hash_value: str, signature_value: str, timeout: int = 15,
) -> Tuple[bool, bool, str]:
    """Returns: (success, is_valid, error_message)"""
    try:
        request = hash_sign_pb2.SignatureVerifyRequest(
            artifact_id=artifact_id,
            hash_value=hash_value,
            signature_value=signature_value,
            signature_algorithm="RSA-SHA256",
        )
        response = _stub.VerifySignature(request, timeout=timeout)
        if response.success:
            return True, response.signature_valid, ""
        return False, False, response.error_message
    except grpc.RpcError as e:
        return False, False, f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, False, f"Internal Error: {str(e)}"


async def verify_signature_async(
    artifact_id: str, hash_value: str, signature_value: str, timeout: int = 15,
) -> Tuple[bool, bool, str]:
    return await asyncio.to_thread(verify_signature, artifact_id, hash_value, signature_value, timeout)
