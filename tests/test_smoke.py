"""
Smoke tests: verify that the gateway is reachable and all seed users
can authenticate successfully.
"""

import requests
import pytest

GATEWAY = "http://localhost:8080"
BASE_URL = f"{GATEWAY}/api"


def test_gateway_health():
    """Gateway exposes a no-auth health endpoint that proxies to evidence-service."""
    r = requests.get(f"{GATEWAY}/health")
    assert r.status_code == 200


@pytest.mark.parametrize("username,password", [
    ("admin01", "admin01"),
    ("investigator01", "investigator01"),
    ("analyst01", "analyst01"),
    ("reviewer01", "reviewer01"),
])
def test_login_seed_users(username, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["access_token"]


def test_login_wrong_password():
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin01", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user():
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_unauthenticated_evidence_returns_401():
    r = requests.get(f"{BASE_URL}/evidence")
    assert r.status_code == 401


def test_unauthenticated_admin_returns_401():
    r = requests.get(f"{BASE_URL}/admin/users")
    assert r.status_code == 401
