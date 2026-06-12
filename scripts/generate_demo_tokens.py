"""
Development/debug utility — generates JWT tokens for all four ForensicChain roles.

This is NOT a substitute for the normal login flow (/auth/login). Use it only
when you need a valid token quickly for development or API testing without
going through the auth service.

Usage:
    python scripts/generate_demo_tokens.py

The script reads JWT_SECRET from the environment. Set it to the same value
configured for the auth service (jwt_secret in .env), otherwise generated
tokens will be rejected.

    JWT_SECRET=your-secret python scripts/generate_demo_tokens.py
"""

import datetime
import os
import sys

try:
    import jwt
except ImportError:
    sys.exit("PyJWT is not installed. Run: pip install PyJWT")

SECRET: str = os.environ.get("JWT_SECRET", "changeme-use-a-strong-random-secret-in-production")
ALGORITHM: str = "HS256"
EXPIRY_HOURS: int = 8

DEMO_USERS: list[dict] = [
    {"sub": "investigator01", "role": "investigator",      "name": "Demo Investigator"},
    {"sub": "analyst01",      "role": "forensic_analyst",  "name": "Demo Analyst"},
    {"sub": "reviewer01",     "role": "legal_reviewer",    "name": "Demo Reviewer"},
    {"sub": "admin01",        "role": "admin",             "name": "Demo Admin"},
]


def generate_token(user: dict, now: datetime.datetime) -> str:
    payload = {
        **user,
        "iat": now,
        "exp": now + datetime.timedelta(hours=EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def main() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(hours=EXPIRY_HOURS)

    print("=" * 80)
    print("FORENSICCHAIN DEMO JWT TOKENS  [development/debug only]")
    print(f"Algorithm : {ALGORITHM}")
    print(f"Generated : {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"Expires   : {expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')}  ({EXPIRY_HOURS} hours)")
    print("=" * 80)

    for user in DEMO_USERS:
        token = generate_token(user, now)
        print(f"\n[{user['role']}]  {user['name']}")
        print(f"  Bearer {token}")

    print("\n" + "=" * 80)
    print("Usage example:")
    print("  curl -H 'Authorization: Bearer <token>' http://localhost:8080/evidence")
    print("=" * 80)


if __name__ == "__main__":
    main()
