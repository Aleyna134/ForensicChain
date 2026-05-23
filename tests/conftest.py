"""
Session-scoped fixtures that bootstrap shared state for all test modules.

Setup flow:
  1. Admin logs in.
  2. Admin creates a test case (CASE-2099-001).
  3. Admin assigns investigator01, analyst01, reviewer01 to the case.
  4. Investigator01 uploads a small evidence file.
  5. Returns artifact_id and case_number for downstream tests.
"""

import io
import pytest
import requests

BASE_URL = "http://localhost:8080/api"
TEST_CASE_NUMBER = "CASE-2099-001"
TEST_CASE_TITLE = "Automated Test Case"
EVIDENCE_CONTENT = b"ForensicChain automated test evidence payload."


def _login(username: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=10)
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token() -> str:
    return _login("admin01", "admin01")


@pytest.fixture(scope="session")
def investigator_token() -> str:
    return _login("investigator01", "investigator01")


@pytest.fixture(scope="session")
def analyst_token() -> str:
    return _login("analyst01", "analyst01")


@pytest.fixture(scope="session")
def reviewer_token() -> str:
    return _login("reviewer01", "reviewer01")


@pytest.fixture(scope="session")
def setup_case_and_artifact(admin_token, investigator_token) -> dict:
    """
    Creates the test case, assigns all non-admin users, uploads evidence,
    and returns {"artifact_id": ..., "case_number": ..., "case_id": ...}.
    """
    # ── 1. Create case (idempotent: skip 409 if already exists) ──────────
    r = requests.post(
        f"{BASE_URL}/admin/cases",
        json={"case_number": TEST_CASE_NUMBER, "title": TEST_CASE_TITLE},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code in (201, 409), f"Create case: {r.text}"

    # Fetch case id
    r = requests.get(f"{BASE_URL}/admin/cases", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    cases = r.json()
    case = next((c for c in cases if c["case_number"] == TEST_CASE_NUMBER), None)
    assert case is not None, "Test case not found after creation"
    case_id = case["id"]

    # ── 2. Assign users (idempotent: skip 409) ────────────────────────────
    for username, role in [
        ("investigator01", "investigator"),
        ("analyst01", "forensic_analyst"),
        ("reviewer01", "legal_reviewer"),
    ]:
        r = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/assignments",
            json={"username": username, "role_in_case": role},
            headers=_auth(admin_token),
            timeout=10,
        )
        assert r.status_code in (201, 409), f"Assign {username}: {r.text}"

    # ── 3. Upload evidence as investigator ────────────────────────────────
    r = requests.post(
        f"{BASE_URL}/evidence",
        data={
            "case_id": TEST_CASE_NUMBER,
            "title": "Automated Test Evidence",
            "artifact_type": "Other",
            "description": "Created by automated test suite",
        },
        files={"file": ("test_evidence.bin", io.BytesIO(EVIDENCE_CONTENT), "application/octet-stream")},
        headers=_auth(investigator_token),
        timeout=60,
    )
    assert r.status_code == 201, f"Upload evidence: {r.text}"
    artifact_id = r.json()["artifact_id"]

    return {"artifact_id": artifact_id, "case_number": TEST_CASE_NUMBER, "case_id": case_id}


@pytest.fixture(scope="session")
def artifact_id(setup_case_and_artifact) -> str:
    return setup_case_and_artifact["artifact_id"]


@pytest.fixture(scope="session")
def case_number(setup_case_and_artifact) -> str:
    return setup_case_and_artifact["case_number"]
