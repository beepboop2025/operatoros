"""
JWT creation / verification and password hashing utilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.schemas.auth import TokenPayload

settings = get_settings()

# ── Password hashing ────────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if *plain_password* matches *hashed_password*."""
    return _pwd_ctx.verify(plain_password, hashed_password)


# ── JWT ──────────────────────────────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT.

    *data* must contain at minimum ``sub`` (user id) and ``role``.
    """
    to_encode = data.copy()
    # Distinguish access from refresh tokens so an access token cannot be
    # replayed at the /refresh endpoint (and vice versa).
    to_encode.setdefault("type", "access")

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    # Ensure sub is a string for JSON serialisation
    if "sub" in to_encode and isinstance(to_encode["sub"], UUID):
        to_encode["sub"] = str(to_encode["sub"])

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed refresh JWT (``type=refresh``, longer-lived than access)."""
    to_encode = data.copy()
    to_encode["type"] = "refresh"
    return create_access_token(
        to_encode,
        expires_delta=expires_delta or timedelta(days=7),
    )


def verify_token(token: str, expected_type: str | None = None) -> TokenPayload:
    """
    Decode and validate *token*.

    Returns a ``TokenPayload`` on success; raises 401 on any failure. When
    *expected_type* is given (``access``/``refresh``), the token's ``type``
    claim must match, else a 401 is raised.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        sub: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        exp = payload.get("exp")

        if sub is None or role is None:
            raise credentials_exception

        if expected_type is not None and payload.get("type") != expected_type:
            raise credentials_exception

        return TokenPayload(
            sub=UUID(sub),
            role=role,
            exp=datetime.fromtimestamp(exp, tz=timezone.utc),
        )
    except (JWTError, ValueError, KeyError) as exc:
        raise credentials_exception from exc
