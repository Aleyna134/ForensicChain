import jwt
import requests
import datetime

SECRET = "dev-secret-key-change-in-production"

# Generate valid token
payload = {
    "sub": "user-investigator",
    "role": "Investigator",
    "iat": datetime.datetime.utcnow(),
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
}
token = jwt.encode(payload, SECRET, algorithm="HS256")

headers = {
    "Authorization": f"Bearer {token}",
    "X-User-Id": "user-investigator",
    "X-User-Role": "Investigator",
    "X-Correlation-Id": "test-uuid"
}

files = {"file": ("test.txt", b"test content")}
data = {"case_id": "TEST_CASE", "title": "TEST", "artifact_type": "Document"}
resp = requests.post("http://localhost:8001/evidence", headers=headers, files=files, data=data)
print(resp.status_code, resp.text)
