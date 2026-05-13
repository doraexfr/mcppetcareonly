from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from typing import Any, Dict

import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.exceptions import ForbiddenError


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise ForbiddenError("Invalid or expired token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ForbiddenError("Invalid token subject")
    return subject


def verify_login_password(password: str) -> bool:
    return compare_digest(password, settings.AUTH_DEMO_PASSWORD)
