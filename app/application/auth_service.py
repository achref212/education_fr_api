import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.core.email_validation import InvalidEmailError, validate_real_email
from app.core.security import (
    create_access_token,
    create_password_reset_state_token,
    create_password_reset_token,
    create_registration_state_token,
    create_school_token,
    decode_password_reset_state_token,
    decode_password_reset_token,
    decode_registration_state_token,
    hash_password,
    verify_password,
)
from app.domain.entities import School, User
from app.domain.ports import IAdminUserRepository, IEmailSender, ISchoolRepository, IUserRepository

_RESET_CODE_DIGITS = 6
_GENERATED_PASSWORD_BYTES = 12


class AuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _generate_password() -> str:
    return secrets.token_urlsafe(_GENERATED_PASSWORD_BYTES)


class AuthService:
    def __init__(
        self,
        users: IUserRepository,
        email_sender: IEmailSender | None = None,
        reset_expire_minutes: int = 15,
        schools: ISchoolRepository | None = None,
        admin_users: IAdminUserRepository | None = None,
        dashboard_url: str = "https://dashboard.delfy.app",
    ) -> None:
        self._users = users
        self._email_sender = email_sender
        self._reset_expire_minutes = reset_expire_minutes
        self._schools = schools
        self._admin_users = admin_users
        self._dashboard_url = dashboard_url

    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        level: str,
        phone: str | None = None,
        date_of_birth: date | None = None,
        class_level: str | None = None,
        school_id: str | None = None,
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
            phone=phone,
            date_of_birth=date_of_birth,
            class_level=class_level,
            school_id=school_id,
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

    def login_school(self, email: str, password: str) -> tuple[School, str]:
        """Authenticate a school account. Returns (school, access_token)."""
        if self._schools is None:
            raise AuthError("school_login_unavailable", "Connexion école non disponible")

        row = self._schools.get_by_email(email)
        if row is None or not verify_password(password, row.password_hash):
            raise AuthError("invalid_credentials", "E-mail ou mot de passe incorrect")
        if not row.school.is_active:
            raise AuthError("account_inactive", "Compte école désactivé")

        token = create_school_token(row.school.id)
        return row.school, token

    def create_school_account(
        self,
        name: str,
        email: str,
        admin_id: UUID,
        address: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        phone: str | None = None,
        director_name: str | None = None,
    ) -> tuple[School, str]:
        """Admin creates a school. Returns (school, plain_password). Sends welcome email."""
        if self._schools is None:
            raise AuthError("schools_unavailable", "Gestion des écoles non disponible")

        try:
            email = validate_real_email(email)
        except InvalidEmailError as exc:
            raise AuthError("invalid_email", exc.message) from exc

        if self._schools.get_by_email(email):
            raise AuthError("email_taken", "Cet e-mail est déjà utilisé par une école")

        plain_password = _generate_password()
        ph = hash_password(plain_password)

        school = self._schools.create(
            name=name,
            email=email,
            password_hash=ph,
            created_by_admin_id=admin_id,
            address=address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            director_name=director_name,
            must_change_password=True,
        )

        if self._email_sender:
            self._email_sender.send_school_welcome(
                to_email=school.email,
                school_name=school.name,
                plain_password=plain_password,
                dashboard_url=self._dashboard_url,
            )

        return school, plain_password

    def create_prof_account(
        self,
        first_name: str,
        last_name: str,
        email: str,
        teacher_school_id: UUID,
        phone: str | None = None,
        date_of_birth: date | None = None,
    ) -> tuple[User, str]:
        """School creates a professor account. Returns (user, plain_password). Sends welcome email."""
        if self._admin_users is None:
            raise AuthError("admin_users_unavailable", "Gestion des utilisateurs non disponible")

        try:
            email = validate_real_email(email)
        except InvalidEmailError as exc:
            raise AuthError("invalid_email", exc.message) from exc

        if self._users.get_by_email(email):
            raise AuthError("email_taken", "Cet e-mail est déjà utilisé")

        plain_password = _generate_password()
        ph = hash_password(plain_password)

        prof = self._admin_users.create_user_with_role(
            email=email,
            password_hash=ph,
            first_name=first_name,
            last_name=last_name,
            level="prof",
            role="prof",
            teacher_school_id=teacher_school_id,
            phone=phone,
            date_of_birth=date_of_birth,
            must_change_password=True,
        )

        if self._email_sender:
            self._email_sender.send_prof_welcome(
                to_email=prof.email,
                prof_name=f"{first_name} {last_name}",
                plain_password=plain_password,
                dashboard_url=self._dashboard_url,
            )

        return prof, plain_password

    def change_password(self, account: User | School, old_password: str, new_password: str) -> None:
        """Change password for a logged-in User or School."""
        if isinstance(account, User):
            row = self._users.get_by_id(account.id)
            if row is None:
                raise AuthError("account_not_found", "Compte introuvable")
            with_hash = self._users.get_by_email(row.email)
            if with_hash is None or not verify_password(old_password, with_hash.password_hash):
                raise AuthError("invalid_credentials", "Ancien mot de passe incorrect")
            
            self._users.change_password(account.id, hash_password(new_password))
        
        elif isinstance(account, School):
            if self._schools is None:
                raise AuthError("schools_unavailable", "Gestion des écoles non disponible")
            row = self._schools.get_by_id(account.id)
            if row is None:
                raise AuthError("account_not_found", "Compte école introuvable")
            with_hash = self._schools.get_by_email(row.email)
            if with_hash is None or not verify_password(old_password, with_hash.password_hash):
                raise AuthError("invalid_credentials", "Ancien mot de passe incorrect")
            
            self._schools.change_password(account.id, hash_password(new_password))
        
        else:
            raise AuthError("invalid_account_type", "Type de compte invalide")

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
