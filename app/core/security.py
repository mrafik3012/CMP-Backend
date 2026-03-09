"""JWT and password hashing. FR-AUTH-001, FR-AUTH-002."""
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int, remember_me: bool | None = None) -> str:
    if remember_me is None:
        days = settings.refresh_token_expire_days
    elif remember_me:
        days = settings.refresh_token_expire_days_long
    else:
        days = settings.refresh_token_expire_days_short
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16),  # unique id so each token hashes differently (avoids UNIQUE constraint on rapid logins)
    }
    # Persist the remember_me flag so refresh flows preserve the same duration
    if remember_me is not None:
        to_encode["remember_me"] = remember_me
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
