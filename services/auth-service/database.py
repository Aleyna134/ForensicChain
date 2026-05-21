from collections.abc import AsyncGenerator

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class _DBSettings(BaseSettings):
    auth_db_url: str = (
        "postgresql+asyncpg://forensic:forensic_pass@auth-db:5432/auth_db"
    )

    class Config:
        env_file = ".env"


_settings = _DBSettings()

engine = create_async_engine(_settings.auth_db_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    # seed_predefined_users skips rows that already exist, so it is idempotent for
    # existing users. However, if you rebuild the image with a changed _SEED_USERS
    # list and the volume already has the old rows, the new users won't be added
    # until the volume is wiped:
    #   docker volume rm forensicchain_auth_db_data
    # (Docker Compose prefixes the project name, typically the repo directory name.)
    from models import Base  # late import avoids circular dependency at module load

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from repository import seed_predefined_users  # same reason

    await seed_predefined_users()
