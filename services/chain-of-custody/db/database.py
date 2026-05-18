import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# asyncpg requires the postgresql+asyncpg:// scheme.
# The .env uses plain postgresql:// — replace without touching the env file.
_raw_url: str = os.environ["CUSTODY_DB_URL"]
DATABASE_URL: str = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# expire_on_commit=False: prevents SQLAlchemy from expiring attributes after
# commit, which would trigger lazy loads on a closed async session.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
