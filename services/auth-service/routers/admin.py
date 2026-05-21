import bcrypt
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_ROLES = {"investigator", "forensic_analyst", "legal_reviewer"}


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateUserIn(BaseModel):
    username: str
    password: str
    role: str


def _require_admin(x_user_role: str | None) -> None:
    if x_user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("/users", response_model=list[UserOut])
async def list_users(
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserIn,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    if body.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(ALLOWED_ROLES))}",
        )

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(username=body.username, hashed_password=hashed, role=body.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    x_username: str | None = Header(default=None, alias="x-username"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.username == x_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    await db.delete(user)
    await db.commit()
