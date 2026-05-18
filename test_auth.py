import jwt
import requests
import datetime
import uuid

SECRET = "dev-secret-key-change-in-production"

# Generate valid token
payload = {
    "sub": "user-reviewer",
    "role": "LegalReviewer",
    "iat": datetime.datetime.utcnow(),
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
}
token = jwt.encode(payload, SECRET, algorithm="HS256")

# 1. Test missing token
resp = requests.get("http://localhost:8001/internal/auth/validate")
assert resp.status_code == 401

# 2. Test valid token but forbidden (Reviewer trying to POST /evidence)
headers = {
    "Authorization": f"Bearer {token}",
    "X-Original-URI": "/evidence",
    "X-Original-Method": "POST"
}
resp = requests.get("http://localhost:8001/internal/auth/validate", headers=headers)
assert resp.status_code == 403

# 3. Test valid token and allowed (Reviewer trying to POST /evidence/abc/verify)
headers = {
    "Authorization": f"Bearer {token}",
    "X-Original-URI": "/evidence/abc/verify",
    "X-Original-Method": "POST"
}
resp = requests.get("http://localhost:8001/internal/auth/validate", headers=headers)
assert resp.status_code == 200
assert resp.headers["X-User-Id"] == "user-reviewer"
assert resp.headers["X-User-Role"] == "LegalReviewer"
assert "X-Correlation-Id" in resp.headers # Generated

# 4. Test missing correlation ID passed from external
headers = {
    "Authorization": f"Bearer {token}",
    "X-Original-URI": "/reports/",
    "X-Original-Method": "POST",
    "X-Correlation-Id": "provided-corr-id"
}
resp = requests.get("http://localhost:8001/internal/auth/validate", headers=headers)
assert resp.status_code == 200
assert resp.headers["X-Correlation-Id"] == "provided-corr-id"

print("All auth tests passed!")
