"""
JWT token generation and validation.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from uuid import UUID

from backend.config import settings


@dataclass
class TokenPayload:
    """Decoded token payload with user information."""
    user_id: UUID
    role: str


def create_access_token(
    user_id: UUID,
    role: str = "user",
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's UUID
        role: User's role (user or admin)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": now,
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")
        if user_id is None:
            return None
        return TokenPayload(user_id=UUID(user_id), role=role)
    except (JWTError, ValueError):
        return None
