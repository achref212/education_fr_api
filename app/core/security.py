from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_PASSWORD_RESET_PURPOSE = "password_reset"
_PASSWORD_RESET_STATE_PURPOSE = "password_reset_state"


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


_SCHOOL_PREFIX = "school:"


def create_school_token(school_id: UUID, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": f"{_SCHOOL_PREFIX}{school_id}",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def parse_school_id(sub: str) -> UUID | None:
    if not sub.startswith(_SCHOOL_PREFIX):
        return None
    try:
        return UUID(sub[len(_SCHOOL_PREFIX):])
    except ValueError:
        return None


_REGISTRATION_PURPOSE = "registration_activation"

def create_registration_state_token(
    user_id: UUID,
    code_hash: str,
    expires_minutes: int,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "code_hash": code_hash,
        "purpose": _REGISTRATION_PURPOSE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


@dataclass
class RegistrationStateData:
    user_id: UUID
    code_hash: str


def decode_registration_state_token(token: str) -> RegistrationStateData | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

    if payload.get("purpose") != _REGISTRATION_PURPOSE:
        return None

    user_id = parse_user_id(payload.get("sub", ""))
    code_hash = payload.get("code_hash", "")
    if user_id is None or not code_hash:
        return None

    return RegistrationStateData(user_id=user_id, code_hash=code_hash)


@dataclass
class PasswordResetStateData:
    user_id: UUID
    code_hash: str


def create_password_reset_state_token(
    user_id: UUID,
    code_hash: str,
    password_hash: str,
    expires_minutes: int,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "code_hash": code_hash,
        "pwd_hash": password_hash,
        "purpose": _PASSWORD_RESET_STATE_PURPOSE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_state_token(token: str, current_password_hash: str) -> PasswordResetStateData | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

    if payload.get("purpose") != _PASSWORD_RESET_STATE_PURPOSE:
        return None

    if payload.get("pwd_hash") != current_password_hash:
        return None

    user_id = parse_user_id(payload.get("sub", ""))
    code_hash = payload.get("code_hash", "")
    if user_id is None or not code_hash:
        return None

    return PasswordResetStateData(user_id=user_id, code_hash=code_hash)


@dataclass
class PasswordResetTokenData:
    user_id: UUID


def create_password_reset_token(
    user_id: UUID,
    password_hash: str,
    expires_minutes: int,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "pwd_hash": password_hash,
        "purpose": _PASSWORD_RESET_PURPOSE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_token(token: str, current_password_hash: str) -> PasswordResetTokenData | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

    if payload.get("purpose") != _PASSWORD_RESET_PURPOSE:
        return None

    if payload.get("pwd_hash") != current_password_hash:
        return None

    user_id = parse_user_id(payload.get("sub", ""))
    if user_id is None:
        return None

    return PasswordResetTokenData(user_id=user_id)
