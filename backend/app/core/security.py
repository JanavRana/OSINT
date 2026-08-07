"""
Security utilities: password hashing, JWT creation/decoding, OTP generation.
"""

import random
import string
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# bcrypt password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ─────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Encode a JWT access token with an expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode a JWT, returning the payload dict or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Generate a 6-digit numeric OTP code."""
    return "".join(random.choices(string.digits, k=6))


def get_otp_expiry() -> datetime:
    """Return the expiry timestamp for a freshly generated OTP."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
