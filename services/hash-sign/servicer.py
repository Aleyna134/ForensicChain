from datetime import datetime, timezone
import grpc
import hash_sign_pb2
import hash_sign_pb2_grpc
from crypto.hasher import compute_sha256
from crypto.signer import sign_hash, verify_signature

class HashSignServicer(hash_sign_pb2_grpc.HashSignServiceServicer):
    def ComputeAndSignHash(self, request, context):
        try:
            # 1. Compute SHA-256
            hash_hex = compute_sha256(request.file_path)
            
            # 2. Sign the hash
            signature_b64 = sign_hash(hash_hex)
            
            # 3. Create response
            return hash_sign_pb2.IntegrityProofResponse(
                artifact_id=request.artifact_id,
                case_id=request.case_id,
                hash_algorithm="SHA-256",
                hash_value=hash_hex,
                signature_algorithm="RSA-SHA256",
                signature_value=signature_b64,
                signer_id="hash-sign-service",
                signed_at=datetime.now(timezone.utc).isoformat(),
                success=True,
                error_message=""
            )
        except Exception as e:
            return hash_sign_pb2.IntegrityProofResponse(
                artifact_id=request.artifact_id,
                case_id=request.case_id,
                hash_algorithm="SHA-256",
                success=False,
                error_message=str(e)
            )

    def RecomputeHash(self, request, context):
        try:
            hash_hex = compute_sha256(request.file_path)
            return hash_sign_pb2.HashResponse(
                artifact_id=request.artifact_id,
                hash_algorithm="SHA-256",
                hash_value=hash_hex,
                success=True,
                error_message=""
            )
        except Exception as e:
            return hash_sign_pb2.HashResponse(
                artifact_id=request.artifact_id,
                hash_algorithm="SHA-256",
                success=False,
                error_message=str(e)
            )

    def VerifySignature(self, request, context):
        try:
            is_valid = verify_signature(request.hash_value, request.signature_value)
            return hash_sign_pb2.SignatureVerifyResponse(
                artifact_id=request.artifact_id,
                signature_valid=is_valid,
                success=True,
                error_message=""
            )
        except Exception as e:
            return hash_sign_pb2.SignatureVerifyResponse(
                artifact_id=request.artifact_id,
                signature_valid=False,
                success=False,
                error_message=str(e)
            )
