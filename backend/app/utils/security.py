"""
JWT authentication and password hashing utilities.

Uses bcrypt for passwords and python-jose for JWT tokens.
"""

from __future__ import annotations

import os
import hashlib
import secrets
import warnings
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import bcrypt
from jose import JWTError, jwt

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")

# SECURITY: Generate secure JWT secret if not provided
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # Development mode: generate a random secret with warning
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is REQUIRED in production. "
            "Set it in your .env file or environment variables."
        )
    # Development fallback: generate random secret
    JWT_SECRET_KEY = secrets.token_urlsafe(64)
    warnings.warn(
        "JWT_SECRET_KEY not set - using auto-generated secret for development. "
        "This will change on restart and invalidate all tokens. "
        "Set JWT_SECRET_KEY in .env for persistent sessions.",
        UserWarning,
        stacklevel=2
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

PASSWORD_HASH_PREFIX = "bcrypt_sha256$"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def _legacy_bcrypt_bytes(password: str) -> bytes:
    """Legacy bcrypt compatibility path for previously stored hashes."""
    return password.encode("utf-8")[:72]


def _sha256_bcrypt_bytes(password: str) -> bytes:
    """
    Stable password material for new hashes.

    Bcrypt only accepts up to 72 bytes. We pre-hash with SHA-256 so new
    passwords can be arbitrary length/Unicode without truncation.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    """Hash a plaintext password using SHA-256 + bcrypt."""
    hashed = bcrypt.hashpw(_sha256_bcrypt_bytes(password), bcrypt.gensalt())
    return f"{PASSWORD_HASH_PREFIX}{hashed.decode('utf-8')}"


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against its stored hash.

    Supports:
    - new `bcrypt_sha256$...` hashes
    - legacy raw bcrypt hashes already stored in the database
    """
    try:
        if hashed.startswith(PASSWORD_HASH_PREFIX):
            encoded_hash = hashed[len(PASSWORD_HASH_PREFIX):].encode("utf-8")
            return bcrypt.checkpw(_sha256_bcrypt_bytes(plain), encoded_hash)
        return bcrypt.checkpw(_legacy_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_ACCESS_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns None on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
