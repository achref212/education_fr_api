from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities import User
from app.domain.ports import IUserRepository


class AuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        level: str,
    ) -> tuple[User, str]:
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
