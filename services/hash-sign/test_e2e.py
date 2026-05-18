import os
import sys

# Test importing the generated stubs
try:
    import hash_sign_pb2
    import hash_sign_pb2_grpc
    print("SUCCESS: Successfully imported hash_sign_pb2 and hash_sign_pb2_grpc.")
except Exception as e:
    print(f"FAILED to import generated stubs: {e}")
    sys.exit(1)

from servicer import HashSignServicer
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone
import base64

# Setup test environment
os.makedirs("/keys", exist_ok=True)
os.makedirs("/evidence-storage", exist_ok=True)

# Generate test keys
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
with open("/keys/private_key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
public_key = private_key.public_key()
with open("/keys/public_key.pem", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

# Create a test file
test_file_path = "/evidence-storage/test.bin"
with open(test_file_path, "wb") as f:
    f.write(b"Test evidence data for hashing and signing.")

# Mock gRPC Context
class MockContext:
    def __init__(self):
        pass

# Initialize servicer
servicer = HashSignServicer()

print("\n--- Testing ComputeAndSignHash ---")
# Create request
req = hash_sign_pb2.ArtifactHashRequest(
    artifact_id="test-123",
    case_id="case-456",
    file_path=test_file_path,
    file_name="test.bin",
    file_size=43,
    hash_algorithm="SHA-256"
)

# Call method
response = servicer.ComputeAndSignHash(req, MockContext())
print(f"Success: {response.success}")
print(f"Hash: {response.hash_value}")
print(f"Signature (base64): {response.signature_value[:30]}...")

assert response.success == True, "ComputeAndSignHash failed"
original_hash = response.hash_value
original_signature = response.signature_value

print("\n--- Testing VerifySignature (Success) ---")
verify_req = hash_sign_pb2.SignatureVerifyRequest(
    artifact_id="test-123",
    hash_value=original_hash,
    signature_value=original_signature,
    signature_algorithm="RSA-SHA256"
)

verify_response = servicer.VerifySignature(verify_req, MockContext())
print(f"Success: {verify_response.success}")
print(f"Signature Valid: {verify_response.signature_valid}")

assert verify_response.success == True, "VerifySignature execution failed"
assert verify_response.signature_valid == True, "VerifySignature validation failed on correct hash"

print("\n--- Testing VerifySignature (Failure after hash modification) ---")
# Modify hash
modified_hash = "deadbeef" + original_hash[8:]
verify_req_fail = hash_sign_pb2.SignatureVerifyRequest(
    artifact_id="test-123",
    hash_value=modified_hash,
    signature_value=original_signature,
    signature_algorithm="RSA-SHA256"
)

verify_fail_response = servicer.VerifySignature(verify_req_fail, MockContext())
print(f"Success: {verify_fail_response.success}")
print(f"Signature Valid: {verify_fail_response.signature_valid}")

assert verify_fail_response.success == True, "VerifySignature execution failed"
assert verify_fail_response.signature_valid == False, "VerifySignature unexpectedly validated a modified hash"

print("\nALL TESTS PASSED!")
