import secrets
from datetime import datetime, timedelta, timezone

from app.core.email_validation import InvalidEmailError, validate_real_email
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.domain.entities import User
from app.domain.ports import IEmailSender, IPasswordResetRepository, IUserRepository

_MAX_RESET_ATTEMPTS = 5
_RESET_CODE_DIGITS = 6


class AuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(
        self,
        users: IUserRepository,
        password_resets: IPasswordResetRepository | None = None,
        email_sender: IEmailSender | None = None,
        reset_expire_minutes: int = 15,
    ) -> None:
        self._users = users
        self._password_resets = password_resets
        self._email_sender = email_sender
        self._reset_expire_minutes = reset_expire_minutes

    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        level: str,
    ) -> tuple[User, str]:
        try:
            email = validate_real_email(email)
        except InvalidEmailError as exc:
            raise AuthError("invalid_email", exc.message) from exc

        if self._users.get_by_email(email):
            raise AuthError("email_taken", "Cet e-mail est déjà utilisé")

        ph = hash_password(password)
        user = self._users.create_user(
            email=email,
            password_hash=ph,
            first_name=first_name,
            last_name=last_name,
            level=level,
        )
        token = create_access_token(str(user.id))
        return user, token

    def login(self, email: str, password: str) -> tuple[User, str]:
        row = self._users.get_by_email(email)
        if row is None or not verify_password(password, row.password_hash):
            raise AuthError("invalid_credentials", "E-mail ou mot de passe incorrect")
        if not row.user.is_active:
            raise AuthError("account_inactive", "Compte désactivé")
        token = create_access_token(str(row.user.id))
        return row.user, token

    def request_password_reset(self, email: str) -> None:
        """Initiate a password reset.  Always returns silently (avoids enumeration)."""
        if self._password_resets is None or self._email_sender is None:
            return

        row = self._users.get_by_email(email)
        if row is None:
            return

        user = row.user

        self._password_resets.invalidate_all_for_user(user.id)

        raw_code = f"{secrets.randbelow(10 ** _RESET_CODE_DIGITS):0{_RESET_CODE_DIGITS}d}"
        code_hash = hash_password(raw_code)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._reset_expire_minutes
        )

        self._password_resets.create(
            user_id=user.id,
            code_hash=code_hash,
            expires_at=expires_at,
        )

        self._email_sender.send_password_reset_code(
            to_email=user.email,
            to_name=user.first_name,
            code=raw_code,
            expires_minutes=self._reset_expire_minutes,
        )

    def verify_reset_code(self, email: str, code: str) -> str:
        """Verify a 6-digit reset code and return a short-lived reset JWT."""
        if self._password_resets is None:
            raise AuthError("service_unavailable", "Service indisponible")

        row = self._users.get_by_email(email)
        if row is None:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        reset_record = self._password_resets.get_latest_for_user(row.user.id)
        if reset_record is None or reset_record.used:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if reset_record.attempts >= _MAX_RESET_ATTEMPTS:
            raise AuthError(
                "too_many_attempts",
                "Trop de tentatives. Veuillez faire une nouvelle demande.",
            )

        now = datetime.now(timezone.utc)
        expires_at = reset_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if not verify_password(code, reset_record.code_hash):
            self._password_resets.increment_attempts(reset_record.id)
            raise AuthError("invalid_code", "Code invalide ou expiré")

        reset_token = create_password_reset_token(
            user_id=row.user.id,
            code_id=reset_record.id,
            expires_minutes=self._reset_expire_minutes,
        )
        return reset_token

    def reset_password(self, reset_token: str, new_password: str) -> None:
        """Apply the new password after verifying the reset token."""
        if self._password_resets is None:
            raise AuthError("service_unavailable", "Service indisponible")

        token_data = decode_password_reset_token(reset_token)
        if token_data is None:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        reset_record = self._password_resets.get_by_id(token_data.code_id)
        if reset_record is None or reset_record.used:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        now = datetime.now(timezone.utc)
        expires_at = reset_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        if reset_record.user_id != token_data.user_id:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        new_hash = hash_password(new_password)
        self._users.update_password(token_data.user_id, new_hash)
        self._password_resets.mark_used(reset_record.id)
