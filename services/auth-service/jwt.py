from datetime import datetime, timedelta, timezone

from jose import JWTError
from jose import jwt as jose_jwt
from pydantic_settings import BaseSettings


class _JWTSettings(BaseSettings):
    jwt_secret: str = "changeme-use-a-strong-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    class Config:
        env_file = ".env"


_settings = _JWTSettings()


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.jwt_expire_minutes),
    }
    return jose_jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jose_jwt.decode(
            token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
