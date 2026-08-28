import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException


class TokenService:
    """Issues and validates short-lived JWT Access Tokens."""

    @staticmethod
    def create_access_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
        delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        now = datetime.now(timezone.utc)
        expire = now + delta

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": str(uuid.uuid4()),
            "type": "access_token",
        }

        encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "access_token":
                raise DomainException("Invalid token type", code="AUTH_INVALID_TOKEN")
            return payload
        except JWTError:
            raise DomainException("Access token is invalid or expired", code="AUTH_TOKEN_EXPIRED")
