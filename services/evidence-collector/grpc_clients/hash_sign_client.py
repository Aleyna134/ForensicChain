import os
import grpc
from typing import Tuple
from . import hash_sign_pb2
from . import hash_sign_pb2_grpc

HASH_SIGN_HOST = os.getenv("HASH_SIGN_GRPC_HOST", "localhost")
HASH_SIGN_PORT = os.getenv("HASH_SIGN_GRPC_PORT", "50051")
CHANNEL_ADDRESS = f"{HASH_SIGN_HOST}:{HASH_SIGN_PORT}"

def compute_and_sign(artifact_id: str, case_id: str, file_path: str, file_name: str, file_size: int, timeout: int = 15) -> Tuple[bool, str, str, str]:
    """
    Calls the Hash & Sign Service synchronously with a timeout.
    Returns: (success, hash_value, signature_value, error_message)
    """
    try:
        with grpc.insecure_channel(CHANNEL_ADDRESS) as channel:
            stub = hash_sign_pb2_grpc.HashSignServiceStub(channel)
            request = hash_sign_pb2.ArtifactHashRequest(
                artifact_id=artifact_id,
                case_id=case_id,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                hash_algorithm="SHA-256"
            )
            # Apply explicit timeout deadline
            response = stub.ComputeAndSignHash(request, timeout=timeout)
            
            if response.success:
                return True, response.hash_value, response.signature_value, ""
            else:
                return False, "", "", response.error_message
    except grpc.RpcError as e:
        return False, "", "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", "", f"Internal Error: {str(e)}"

def recompute_hash(artifact_id: str, case_id: str, file_path: str, file_name: str, file_size: int, timeout: int = 15) -> Tuple[bool, str, str]:
    """
    Calls RecomputeHash to generate hash for verification without signing.
    Returns: (success, hash_value, error_message)
    """
    try:
        with grpc.insecure_channel(CHANNEL_ADDRESS) as channel:
            stub = hash_sign_pb2_grpc.HashSignServiceStub(channel)
            request = hash_sign_pb2.ArtifactHashRequest(
                artifact_id=artifact_id,
                case_id=case_id,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                hash_algorithm="SHA-256"
            )
            response = stub.RecomputeHash(request, timeout=timeout)
            
            if response.success:
                return True, response.hash_value, ""
            else:
                return False, "", response.error_message
    except grpc.RpcError as e:
        return False, "", f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, "", f"Internal Error: {str(e)}"

def verify_signature(artifact_id: str, hash_value: str, signature_value: str, timeout: int = 15) -> Tuple[bool, bool, str]:
    """
    Calls VerifySignature on Hash & Sign Service.
    Returns: (success, is_valid, error_message)
    """
    try:
        with grpc.insecure_channel(CHANNEL_ADDRESS) as channel:
            stub = hash_sign_pb2_grpc.HashSignServiceStub(channel)
            request = hash_sign_pb2.SignatureVerifyRequest(
                artifact_id=artifact_id,
                hash_value=hash_value,
                signature_value=signature_value,
                signature_algorithm="RSA-SHA256"
            )
            response = stub.VerifySignature(request, timeout=timeout)
            
            if response.success:
                return True, response.signature_valid, ""
            else:
                return False, False, response.error_message
    except grpc.RpcError as e:
        return False, False, f"gRPC Error: {e.details()}"
    except Exception as e:
        return False, False, f"Internal Error: {str(e)}"
