"""
Generate demo JWT tokens for all four ForensicChain roles.

Usage:
    JWT_SECRET=dev-secret-key python scripts/generate_demo_tokens.py

Tokens are valid for 30 days from generation time and are intended
for development and demo use only. Rotate JWT_SECRET before any
production or shared-environment deployment.
"""

import datetime
import os
import sys

try:
    import jwt
except ImportError:
    sys.exit("PyJWT is not installed. Run: pip install PyJWT")

SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-key-change-in-production")
ALGORITHM: str = "HS256"
EXPIRY_DAYS: int = 30

DEMO_USERS: list[dict] = [
    {"sub": "user-investigator", "role": "Investigator",    "name": "Demo Investigator"},
    {"sub": "user-analyst",      "role": "ForensicAnalyst", "name": "Demo Analyst"},
    {"sub": "user-reviewer",     "role": "LegalReviewer",   "name": "Demo Reviewer"},
    {"sub": "user-admin",        "role": "Admin",           "name": "Demo Admin"},
]


def generate_token(user: dict, now: datetime.datetime) -> str:
    payload = {
        **user,
        "iat": now,
        "exp": now + datetime.timedelta(days=EXPIRY_DAYS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def main() -> None:
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=EXPIRY_DAYS)

    print("=" * 80)
    print("FORENSICCHAIN DEMO JWT TOKENS")
    print(f"Algorithm : {ALGORITHM}")
    print(f"Generated : {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"Expires   : {expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')}  ({EXPIRY_DAYS} days)")
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
