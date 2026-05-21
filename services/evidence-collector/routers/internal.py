from fastapi import APIRouter

# Auth validation has moved to auth-service (services/auth-service).
# This router is kept so main.py's include_router call does not break;
# the /internal prefix is no longer exposed through the gateway.
router = APIRouter(prefix="/internal")
