import uuid

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response

from jwt import decode_access_token
from rbac import is_authorized

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/auth/validate")
async def validate(
    authorization: str | None = Header(default=None),
    x_original_uri: str | None = Header(default=None, alias="x-original-uri"),
    x_original_method: str | None = Header(default=None, alias="x-original-method"),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = decode_access_token(authorization.removeprefix("Bearer "))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    role = payload.get("role", "")
    sub = payload.get("sub", "")

    # nginx forwards $request_uri which still has the /api prefix; strip it so
    # rbac.py patterns match /evidence, /custody etc. without the gateway prefix.
    raw_uri = x_original_uri or "/"
    uri = raw_uri.removeprefix("/api")
    method = (x_original_method or "GET").upper()

    if not is_authorized(role, method, uri):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Return identity info as response headers so nginx can capture them via
    # auth_request_set and forward to backend services as X-Username etc.
    corr_id = str(uuid.uuid4())
    resp = Response(status_code=200)
    resp.headers["X-Username"]       = sub
    resp.headers["X-User-Id"]        = sub
    resp.headers["X-User-Role"]      = role
    resp.headers["X-Correlation-Id"] = corr_id
    return resp
