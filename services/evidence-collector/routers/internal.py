from fastapi import APIRouter, Request, Response, HTTPException
import jwt
import os
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")

# Role -> list of rule tuples.
# 2-tuple  (method, path_prefix)        : method + prefix match only.
# 3-tuple  (method, path_prefix, suffix): also requires uri.endswith(suffix).
ROLE_RULES: dict[str, list[tuple]] = {
    "Investigator": [
        ("POST", "/evidence"),
        ("GET",  "/evidence/"),
    ],
    "ForensicAnalyst": [
        ("POST", "/evidence"),
        ("GET",  "/evidence/"),
    ],
    "LegalReviewer": [
        ("GET",  "/evidence/"),          # get artifact metadata
        ("GET",  "/custody/"),
        ("POST", "/reports/"),           # generate report
        ("GET",  "/reports/"),           # metadata + download + verify
        ("POST", "/evidence/", "/verify"),  # only POST .../verify, not upload
    ],
    "Admin": [
        ("GET",  "/"),
        ("POST", "/"),
    ],
}

@router.get("/auth/validate")
async def validate_token(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        return Response(status_code=401)
    
    token = auth[7:]
    
    try:
        # jwt.decode intrinsically validates signature and `exp` (expiration)
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return Response(status_code=401)
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return Response(status_code=401)

    role = payload.get("role", "")
    sub = payload.get("sub", "")
    
    if not role or not sub:
        logger.warning("Token missing role or sub")
        return Response(status_code=401)

    uri = request.headers.get("X-Original-URI", "")
    method = request.headers.get("X-Original-Method", "GET").upper()

    # Method + path prefix (+ optional suffix) RBAC check
    rules = ROLE_RULES.get(role, [])
    allowed = False
    
    if role == "Admin":
        allowed = True
    else:
        for rule in rules:
            if method == rule[0] and uri.startswith(rule[1]):
                if len(rule) == 2 or uri.endswith(rule[2]):
                    allowed = True
                    break

    if not allowed:
        logger.warning(f"Forbidden access: User {sub} (Role: {role}) attempting {method} {uri}")
        return Response(status_code=403)

    # Trust boundary: we generate X-Correlation-Id if not present
    corr_id_in = request.headers.get("X-Correlation-Id")
    corr_id = corr_id_in if corr_id_in else str(uuid.uuid4())

    response = Response(status_code=200)
    response.headers["X-User-Id"] = str(sub)
    response.headers["X-User-Role"] = str(role)
    response.headers["X-Correlation-Id"] = str(corr_id)
    
    return response
