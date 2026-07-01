import secrets
from datetime import datetime, timedelta, timezone

from app.core.email_validation import InvalidEmailError, validate_real_email
from app.core.security import (
    create_access_token,
    create_password_reset_state_token,
    create_password_reset_token,
    create_registration_state_token,
    decode_password_reset_state_token,
    decode_password_reset_token,
    decode_registration_state_token,
    hash_password,
    verify_password,
)
from app.domain.entities import User
from app.domain.ports import IEmailSender, IUserRepository

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
        email_sender: IEmailSender | None = None,
        reset_expire_minutes: int = 15,
    ) -> None:
        self._users = users
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
        """Register a new user and send an activation code. Returns (user, registration_state_token)."""
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
            is_active=False,
        )

        raw_code = f"{secrets.randbelow(10 ** _RESET_CODE_DIGITS):0{_RESET_CODE_DIGITS}d}"
        code_hash = hash_password(raw_code)

        state_token = create_registration_state_token(
            user_id=user.id,
            code_hash=code_hash,
            expires_minutes=self._reset_expire_minutes,
        )

        if self._email_sender:
            self._email_sender.send_activation_code(
                to_email=user.email,
                to_name=user.first_name,
                code=raw_code,
                expires_minutes=self._reset_expire_minutes,
            )

        return user, state_token

    def verify_registration(self, email: str, code: str, state_token: str) -> tuple[User, str]:
        """Verify the activation code and activate the user. Returns (user, access_token)."""
        row = self._users.get_by_email(email)
        if row is None:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if row.user.is_active:
            raise AuthError("already_active", "Compte déjà activé")

        state_data = decode_registration_state_token(state_token)
        if state_data is None:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if state_data.user_id != row.user.id:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if not verify_password(code, state_data.code_hash):
            raise AuthError("invalid_code", "Code invalide ou expiré")

        self._users.activate_user(row.user.id)
        row.user.is_active = True
        
        access_token = create_access_token(str(row.user.id))
        return row.user, access_token

    def resend_activation_code(self, email: str) -> str | None:
        """Resend activation code for an inactive user. Returns new state_token."""
        if self._email_sender is None:
            return None

        row = self._users.get_by_email(email)
        if row is None or row.user.is_active:
            return None

        user = row.user

        raw_code = f"{secrets.randbelow(10 ** _RESET_CODE_DIGITS):0{_RESET_CODE_DIGITS}d}"
        code_hash = hash_password(raw_code)

        state_token = create_registration_state_token(
            user_id=user.id,
            code_hash=code_hash,
            expires_minutes=self._reset_expire_minutes,
        )

        self._email_sender.send_activation_code(
            to_email=user.email,
            to_name=user.first_name,
            code=raw_code,
            expires_minutes=self._reset_expire_minutes,
        )
        
        return state_token

    def login(self, email: str, password: str) -> tuple[User, str]:
        row = self._users.get_by_email(email)
        if row is None or not verify_password(password, row.password_hash):
            raise AuthError("invalid_credentials", "E-mail ou mot de passe incorrect")
        if not row.user.is_active:
            raise AuthError("account_inactive", "Compte désactivé")
        token = create_access_token(str(row.user.id))
        return row.user, token

    def request_password_reset(self, email: str) -> str | None:
        """Initiate a password reset. Returns a state token if user exists."""
        if self._email_sender is None:
            return None

        row = self._users.get_by_email(email)
        if row is None:
            return None

        user = row.user

        raw_code = f"{secrets.randbelow(10 ** _RESET_CODE_DIGITS):0{_RESET_CODE_DIGITS}d}"
        code_hash = hash_password(raw_code)

        state_token = create_password_reset_state_token(
            user_id=user.id,
            code_hash=code_hash,
            password_hash=row.password_hash,
            expires_minutes=self._reset_expire_minutes,
        )

        self._email_sender.send_password_reset_code(
            to_email=user.email,
            to_name=user.first_name,
            code=raw_code,
            expires_minutes=self._reset_expire_minutes,
        )
        
        return state_token

    def verify_reset_code(self, email: str, code: str, state_token: str) -> str:
        """Verify a 6-digit reset code using the state token and return a short-lived reset JWT."""
        row = self._users.get_by_email(email)
        if row is None:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        state_data = decode_password_reset_state_token(state_token, row.password_hash)
        if state_data is None:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if state_data.user_id != row.user.id:
            raise AuthError("invalid_code", "Code invalide ou expiré")

        if not verify_password(code, state_data.code_hash):
            raise AuthError("invalid_code", "Code invalide ou expiré")

        reset_token = create_password_reset_token(
            user_id=row.user.id,
            password_hash=row.password_hash,
            expires_minutes=self._reset_expire_minutes,
        )
        return reset_token

    def reset_password(self, email: str, reset_token: str, new_password: str) -> None:
        """Apply the new password after verifying the reset token."""
        row = self._users.get_by_email(email)
        if row is None:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        token_data = decode_password_reset_token(reset_token, row.password_hash)
        if token_data is None:
            raise AuthError("invalid_token", "Lien de réinitialisation invalide ou expiré")

        new_hash = hash_password(new_password)
        self._users.update_password(token_data.user_id, new_hash)
