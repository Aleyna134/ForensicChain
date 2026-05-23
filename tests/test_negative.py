"""
Negative authorization tests.

Most requests are rejected at the gateway/RBAC layer (401 / 403). Some
tests intentionally verify domain-level authorization, such as preventing
an investigator from accessing another user's artifact. The conftest
fixture provides a real artifact_id so tests that need one don't have to
make up a UUID.

RBAC summary (from services/auth-service/rbac.py):
  investigator    : upload + own evidence metadata/verify; NO custody, ledger, reports, admin
  forensic_analyst: upload + case evidence metadata/verify/download; NO custody, ledger, reports, admin
  legal_reviewer  : evidence metadata/verify + custody + ledger + reports; NO upload, download, admin
  admin           : /admin/* only; NO evidence, custody, ledger, reports
"""

import io
import pytest
import requests

BASE_URL = "http://localhost:8080/api"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── No token → 401 ────────────────────────────────────────────────────────────

def test_no_token_evidence_401():
    r = requests.get(f"{BASE_URL}/evidence", timeout=10)
    assert r.status_code == 401


def test_no_token_admin_401():
    r = requests.get(f"{BASE_URL}/admin/users", timeout=10)
    assert r.status_code == 401


def test_no_token_custody_401(artifact_id):
    r = requests.get(f"{BASE_URL}/custody/{artifact_id}/timeline", timeout=10)
    assert r.status_code == 401


def test_no_token_ledger_401():
    r = requests.get(f"{BASE_URL}/ledger/validate/CASE-2099-001", timeout=10)
    assert r.status_code == 401


def test_no_token_reports_401(artifact_id):
    r = requests.post(f"{BASE_URL}/reports/{artifact_id}", timeout=10)
    assert r.status_code == 401


# ── Admin cannot access evidence ──────────────────────────────────────────────

def test_admin_cannot_list_evidence_403(admin_token):
    r = requests.get(f"{BASE_URL}/evidence", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 403


def test_admin_cannot_upload_evidence_403(admin_token):
    r = requests.post(
        f"{BASE_URL}/evidence",
        data={"case_id": "CASE-2099-001", "title": "t", "artifact_type": "Other"},
        files={"file": ("f.bin", io.BytesIO(b"x"), "application/octet-stream")},
        headers=_auth(admin_token),
        timeout=30,
    )
    assert r.status_code == 403


# ── Legal reviewer cannot download evidence ───────────────────────────────────

def test_reviewer_cannot_download_evidence_403(artifact_id, reviewer_token):
    r = requests.get(
        f"{BASE_URL}/evidence/{artifact_id}/download",
        headers=_auth(reviewer_token),
        timeout=30,
    )
    assert r.status_code == 403


# ── Investigator cannot access custody timeline ───────────────────────────────

def test_investigator_cannot_access_custody_403(artifact_id, investigator_token):
    r = requests.get(
        f"{BASE_URL}/custody/{artifact_id}/timeline",
        headers=_auth(investigator_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Forensic analyst cannot access custody timeline ───────────────────────────

def test_analyst_cannot_access_custody_403(artifact_id, analyst_token):
    r = requests.get(
        f"{BASE_URL}/custody/{artifact_id}/timeline",
        headers=_auth(analyst_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Investigator cannot access ledger ─────────────────────────────────────────

def test_investigator_cannot_access_ledger_403(investigator_token):
    r = requests.get(
        f"{BASE_URL}/ledger/validate/CASE-2099-001",
        headers=_auth(investigator_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Forensic analyst cannot access ledger ────────────────────────────────────

def test_analyst_cannot_access_ledger_403(analyst_token):
    r = requests.get(
        f"{BASE_URL}/ledger/validate/CASE-2099-001",
        headers=_auth(analyst_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Investigator cannot generate reports ─────────────────────────────────────

def test_investigator_cannot_generate_report_403(artifact_id, investigator_token):
    r = requests.post(
        f"{BASE_URL}/reports/{artifact_id}",
        headers=_auth(investigator_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Forensic analyst cannot generate reports ──────────────────────────────────

def test_analyst_cannot_generate_report_403(artifact_id, analyst_token):
    r = requests.post(
        f"{BASE_URL}/reports/{artifact_id}",
        headers=_auth(analyst_token),
        timeout=10,
    )
    assert r.status_code == 403


# ── Legal reviewer cannot upload evidence ─────────────────────────────────────

def test_reviewer_cannot_upload_evidence_403(reviewer_token):
    r = requests.post(
        f"{BASE_URL}/evidence",
        data={"case_id": "CASE-2099-001", "title": "t", "artifact_type": "Other"},
        files={"file": ("f.bin", io.BytesIO(b"x"), "application/octet-stream")},
        headers=_auth(reviewer_token),
        timeout=30,
    )
    assert r.status_code == 403


# ── Non-admin cannot call admin endpoints ─────────────────────────────────────

def test_investigator_cannot_call_admin_403(investigator_token):
    r = requests.get(f"{BASE_URL}/admin/users", headers=_auth(investigator_token), timeout=10)
    assert r.status_code == 403


def test_analyst_cannot_call_admin_403(analyst_token):
    r = requests.get(f"{BASE_URL}/admin/users", headers=_auth(analyst_token), timeout=10)
    assert r.status_code == 403


def test_reviewer_cannot_call_admin_403(reviewer_token):
    r = requests.get(f"{BASE_URL}/admin/users", headers=_auth(reviewer_token), timeout=10)
    assert r.status_code == 403


# ── Investigator cannot access another user's artifact ────────────────────────

def test_investigator_cannot_access_unowned_artifact_403(analyst_token, investigator_token):
    """
    Upload an artifact as analyst, then verify investigator cannot download it
    (investigator download is restricted to own artifacts at the domain level).
    """
    # Upload as analyst (forensic_analyst can upload)
    r = requests.post(
        f"{BASE_URL}/evidence",
        data={"case_id": "CASE-2099-001", "title": "Analyst artifact", "artifact_type": "Other"},
        files={"file": ("f.bin", io.BytesIO(b"analyst evidence"), "application/octet-stream")},
        headers=_auth(analyst_token),
        timeout=60,
    )
    assert r.status_code == 201
    other_artifact_id = r.json()["artifact_id"]

    # Investigator tries to download an artifact they don't own → 403 from domain service
    r = requests.get(
        f"{BASE_URL}/evidence/{other_artifact_id}/download",
        headers=_auth(investigator_token),
        timeout=30,
    )
    assert r.status_code == 403
