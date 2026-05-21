from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.internal import router as internal_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="ForensicChain Auth Service", version="1.0.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}
