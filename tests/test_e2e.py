"""
End-to-end functional test: full ForensicChain workflow.

conftest bootstraps → case created, users assigned, evidence uploaded.

1.  Investigator views artifact metadata.
2.  Analyst requests verification with original content → VALID.
3.  Analyst requests verification with tampered content → TAMPERED.
4.  Analyst downloads the original evidence file.
5.  Legal reviewer fetches chain-of-custody timeline (min 6 events).
6.  Legal reviewer validates ledger chain for the test case.
7.  Legal reviewer lists ledger records.
8.  Legal reviewer generates a PDF report.
9.  Legal reviewer downloads the generated PDF.
10. Legal reviewer lists reports for the artifact.
"""

import io
import time
import pytest
import requests

from conftest import BASE_URL, EVIDENCE_CONTENT


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. View artifact metadata ─────────────────────────────────────────────────

def test_investigator_view_artifact(artifact_id, investigator_token):
    r = requests.get(f"{BASE_URL}/evidence/{artifact_id}", headers=_auth(investigator_token))
    assert r.status_code == 200
    body = r.json()
    assert body["artifact_id"] == artifact_id
    assert body["status"] in ("PENDING", "INGESTED", "INGESTION_FAILED")


# ── 2. Verify original evidence → VALID ──────────────────────────────────────

def test_analyst_verify_original(artifact_id, analyst_token):
    r = requests.post(
        f"{BASE_URL}/evidence/{artifact_id}/verify",
        files={"file": ("original.bin", io.BytesIO(EVIDENCE_CONTENT), "application/octet-stream")},
        headers=_auth(analyst_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verification_result"] == "VALID"
    assert body["signature_valid"] is True
    assert body["ledger_chain_valid"] is True


# ── 3. Verify tampered content → TAMPERED ────────────────────────────────────

def test_analyst_verify_tampered(artifact_id, analyst_token):
    tampered = b"THIS CONTENT HAS BEEN TAMPERED WITH."
    r = requests.post(
        f"{BASE_URL}/evidence/{artifact_id}/verify",
        files={"file": ("tampered.bin", io.BytesIO(tampered), "application/octet-stream")},
        headers=_auth(analyst_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verification_result"] == "TAMPERED"
    # Signature validates the stored original hash, which remains cryptographically valid
    assert body["signature_valid"] is True


# ── 4. Download evidence file ─────────────────────────────────────────────────

def test_analyst_download(artifact_id, analyst_token):
    r = requests.get(
        f"{BASE_URL}/evidence/{artifact_id}/download",
        headers=_auth(analyst_token),
    )
    assert r.status_code == 200
    assert len(r.content) > 0


# ── 5. Chain-of-custody timeline ─────────────────────────────────────────────

def test_custody_timeline(artifact_id, reviewer_token):
    # Allow the outbox worker up to 15 s to propagate all events
    deadline = time.time() + 15
    events = []
    while time.time() < deadline:
        r = requests.get(
            f"{BASE_URL}/custody/{artifact_id}/timeline",
            headers=_auth(reviewer_token),
        )
        assert r.status_code == 200
        events = r.json().get("events", [])
        # EvidenceIngested + EvidenceViewed + VerificationRequested×2
        # + VerificationPassed + VerificationFailed = 6 minimum
        if len(events) >= 6:
            break
        time.sleep(1)

    event_types = [e["event_type"] for e in events]
    assert "EvidenceIngested" in event_types
    assert len(events) >= 6, f"Expected ≥6 custody events, got {len(events)}: {event_types}"


# ── 6. Ledger chain validation ────────────────────────────────────────────────

def test_ledger_chain_valid(case_number, reviewer_token):
    r = requests.get(
        f"{BASE_URL}/ledger/validate/{case_number}",
        headers=_auth(reviewer_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["chain_valid"] is True
    assert body["checked_records"] >= 1


# ── 7. Ledger records listed ──────────────────────────────────────────────────

def test_ledger_records_listed(case_number, reviewer_token):
    r = requests.get(
        f"{BASE_URL}/ledger/records/{case_number}",
        headers=_auth(reviewer_token),
    )
    assert r.status_code == 200
    records = r.json()
    assert isinstance(records, list)
    assert len(records) >= 1
    first = records[0]
    assert "record_hash" in first
    assert "record_type" in first
    assert "artifact_id" in first


# ── 8. Generate PDF report ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def report_id(artifact_id, reviewer_token):
    r = requests.post(
        f"{BASE_URL}/reports/{artifact_id}",
        headers=_auth(reviewer_token),
    )
    assert r.status_code == 201, f"Generate report: {r.text}"
    return r.json()["report_id"]


def test_generate_report(report_id):
    assert report_id


# ── 9. Download PDF ───────────────────────────────────────────────────────────

def test_download_report(report_id, reviewer_token):
    r = requests.get(
        f"{BASE_URL}/reports/{report_id}/download",
        headers=_auth(reviewer_token),
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 1000


# ── 10. List reports for artifact ─────────────────────────────────────────────

def test_list_reports_by_artifact(artifact_id, reviewer_token):
    r = requests.get(
        f"{BASE_URL}/reports/by-artifact/{artifact_id}",
        headers=_auth(reviewer_token),
    )
    assert r.status_code == 200
    reports = r.json()
    assert isinstance(reports, list)
    assert len(reports) >= 1
    assert all("report_id" in rep for rep in reports)
