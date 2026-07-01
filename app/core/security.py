from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_PASSWORD_RESET_PURPOSE = "password_reset"


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        sub: str | None = payload.get("sub")
        return sub
    except JWTError:
        return None


def parse_user_id(sub: str) -> UUID | None:
    try:
        return UUID(sub)
    except ValueError:
        return None


@dataclass
class PasswordResetTokenData:
    user_id: UUID
    code_id: UUID


def create_password_reset_token(
    user_id: UUID,
    code_id: UUID,
    expires_minutes: int,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "code_id": str(code_id),
        "purpose": _PASSWORD_RESET_PURPOSE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_token(token: str) -> PasswordResetTokenData | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

    if payload.get("purpose") != _PASSWORD_RESET_PURPOSE:
        return None

    user_id = parse_user_id(payload.get("sub", ""))
    code_id = parse_user_id(payload.get("code_id", ""))
    if user_id is None or code_id is None:
        return None

    return PasswordResetTokenData(user_id=user_id, code_id=code_id)
