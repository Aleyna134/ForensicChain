import os
import requests
import psycopg2
import time
import uuid

# Configuration
EVIDENCE_URL = "http://localhost:8001/evidence"
EVIDENCE_DB = "postgresql://forensic:forensic_pass@localhost:5433/evidence_db"
LEDGER_DB = "postgresql://forensic:forensic_pass@localhost:5434/ledger_db"

def verify_success_ingestion():
    print("=== Testing Successful Ingestion ===")
    
    # 1. Upload file
    test_content = b"This is a test forensic evidence file content."
    files = {"file": ("test_evidence.txt", test_content, "text/plain")}
    data = {
        "case_id": "CASE-2026-001",
        "title": "Suspect Laptop Memory Dump",
        "artifact_type": "MEMORY_DUMP",
        "description": "Initial memory capture"
    }
    
    headers = {
        "X-User-Id": "investigator_john",
        "X-User-Role": "INVESTIGATOR"
    }
    
    print("Uploading file to Evidence Collector...")
    response = requests.post(EVIDENCE_URL, files=files, data=data, headers=headers)
    
    if response.status_code != 201:
        print(f"FAILED: Expected 201, got {response.status_code}")
        print(response.text)
        return
        
    resp_json = response.json()
    artifact_id = resp_json.get("artifact_id")
    hash_value = resp_json.get("hash_value")
    ledger_record_id = resp_json.get("ledger_record_id")
    
    print(f"Success! Artifact ID: {artifact_id}")
    print(f"Hash: {hash_value}")
    
    if not hash_value or not ledger_record_id:
        print("FAILED: hash_value or ledger_record_id is empty!")
        return
        
    # 2. Check Evidence DB
    print("\nVerifying Evidence DB...")
    with psycopg2.connect(EVIDENCE_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status, hash_value, signature_value FROM artifacts WHERE artifact_id = %s", (artifact_id,))
            row = cur.fetchone()
            if not row:
                print("FAILED: Artifact not found in Evidence DB")
                return
            status, db_hash, db_sig = row
            print(f"DB Status: {status}")
            if status != "INGESTED":
                print(f"FAILED: Status is {status}, expected INGESTED")
                return
            if not db_sig:
                print("FAILED: Signature value is missing in DB")
                return

    # 3. Check Ledger DB
    print("\nVerifying Ledger DB...")
    with psycopg2.connect(LEDGER_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT record_type, payload_hash, record_hash FROM ledger_records WHERE record_id = %s", (ledger_record_id,))
            row = cur.fetchone()
            if not row:
                print("FAILED: Record not found in Ledger DB")
                return
            record_type, payload_hash, record_hash = row
            print(f"Ledger Record Type: {record_type}")
            if record_type != "EVIDENCE_PROOF_CREATED":
                print(f"FAILED: Expected EVIDENCE_PROOF_CREATED, got {record_type}")
                return
                
    print(">>> SUCCESS: Full End-to-End Ingestion Passed!\n")
    return artifact_id

def verify_failure_rollback():
    print("=== Testing Ledger Failure Rollback ===")
    print("NOTE: To test this properly, you must temporarily break the Ledger gRPC connection.")
    print("For example, change LEDGER_GRPC_PORT in .env to a wrong port and restart evidence-service.")
    print("Assuming it is currently broken...")
    
    # Upload file
    test_content = b"This file should be cleaned up."
    files = {"file": ("fail_test.txt", test_content, "text/plain")}
    data = {
        "case_id": "CASE-FAIL",
        "title": "Will Fail",
        "artifact_type": "TEST",
    }
    
    response = requests.post(EVIDENCE_URL, files=files, data=data)
    
    print(f"Response Code: {response.status_code}")
    if response.status_code == 503:
        print("Got expected 503 Service Unavailable.")
        print("Please manually verify that no 'PENDING' record exists in evidence-db for CASE-FAIL.")
        print("Please manually verify that no orphaned directory exists in the evidence_storage volume.")
        print(">>> SUCCESS: Rollback behavior triggered as expected!")
    else:
        print(f"Wait, got {response.status_code}. If 201, the system isn't broken yet! Break it first.")

def test_verification(artifact_id):
    print(f"\n=== Testing Verification for {artifact_id} ===")
    
    # Use the same file to get a VALID result
    test_content = b"This is a test forensic evidence file content."
    files = {"file": ("test_evidence.txt", test_content, "text/plain")}
    data = {"artifact_id": artifact_id}
    
    print("Testing VALID artifact...")
    response = requests.post(f"{EVIDENCE_URL.replace('/evidence', '/verify')}", files=files, data=data)
    print(response.json())
    
    # Use a tampered file
    test_content = b"This is a test forensic evidence file content. TAMPERED!"
    files = {"file": ("test_evidence.txt", test_content, "text/plain")}
    data = {"artifact_id": artifact_id}
    
    print("\nTesting TAMPERED artifact...")
    response = requests.post(f"{EVIDENCE_URL.replace('/evidence', '/verify')}", files=files, data=data)
    print(response.json())

if __name__ == "__main__":
    aid = verify_success_ingestion()
    if aid:
        test_verification(aid)
