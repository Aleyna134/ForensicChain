import os
import uuid

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="ForensicChain — Evidence Collector")

_JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-key-change-in-production")
_ALGORITHM: str = "HS256"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "evidence-collector"}


@app.get("/internal/auth/validate")
async def validate_token(request: Request) -> Response:
    """
    JWT validation endpoint consumed exclusively by the API Gateway via
    auth_request. Returns 200 + identity headers on success, 401 on
    missing/invalid token, 403 on expired token.

    Response headers forwarded by nginx to upstream services:
      X-User-Id        — JWT sub claim
      X-User-Role      — JWT role claim
      X-Correlation-Id — passed through or freshly generated
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return Response(status_code=401)

    token = auth_header.removeprefix("Bearer ")

    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return Response(status_code=403)
    except jwt.PyJWTError:
        return Response(status_code=401)

    corr_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())

    headers = {
        "X-User-Id": payload.get("sub", ""),
        "X-User-Role": payload.get("role", ""),
        "X-Correlation-Id": corr_id,
    }
    return Response(status_code=200, headers=headers)
