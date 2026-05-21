import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import User

# (username, password, role)
_SEED_USERS = [
    ("investigator01", "investigator01", "investigator"),
    ("analyst01",      "analyst01",      "forensic_analyst"),
    ("reviewer01",     "reviewer01",     "legal_reviewer"),
    ("admin01",        "admin01",        "admin"),
]


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def seed_predefined_users() -> None:
    async with AsyncSessionLocal() as db:
        for username, password, role in _SEED_USERS:
            if not await get_user_by_username(db, username):
                db.add(
                    User(
                        username=username,
                        hashed_password=_hash(password),
                        role=role,
                    )
                )
        await db.commit()
