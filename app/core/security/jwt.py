

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


# ================================
# Create JWT Token (Generic)
# ================================
def _create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "type": token_type,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


# ================================
# Public Token Creators
# ================================
def create_access_token(user_id: str) -> str:
    """
    Create short-lived access token.
    """
    expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token({"sub": user_id}, expire, TokenType.ACCESS)


def create_refresh_token(user_id: str) -> str:
    """
    Create long-lived refresh token.
    """
    expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token({"sub": user_id}, expire, TokenType.REFRESH)


# ================================
# Decode & Validate Token
# ================================
def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT and validate signature & expiration.
    Raises JWTError if invalid.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload


# ================================
# Helper Validators
# ================================
def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
    """
    Ensure token is of expected type.
    """
    token_type = payload.get("type")
    if token_type != expected_type:
        raise JWTError(f"Invalid token type. Expected {expected_type}, got {token_type}")


def get_user_id_from_payload(payload: Dict[str, Any]) -> str:
    """
    Extract user id safely.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("Token missing subject")
    return user_id