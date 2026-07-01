"""Unit tests for AuthService with in-memory fakes (no database)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.application.auth_service import AuthError, AuthService
from app.core.security import hash_password
from app.domain.entities import PasswordResetCode, User, UserWithHash
from app.domain.ports import IEmailSender, IPasswordResetRepository, IUserRepository


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeUserRepo(IUserRepository):
    users: list[UserWithHash] = field(default_factory=list)

    def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        level: str,
    ) -> User:
        u = User(
            id=uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            level=level,
            created_at=datetime.now(timezone.utc),
            role="user",
            is_active=True,
        )
        self.users.append(UserWithHash(user=u, password_hash=password_hash))
        return u

    def get_by_email(self, email: str) -> UserWithHash | None:
        for u in self.users:
            if u.user.email == email:
                return u
        return None

    def get_by_id(self, user_id: UUID) -> User | None:
        for u in self.users:
            if u.user.id == user_id:
                return u.user
        return None

    def update_password(self, user_id: UUID, password_hash: str) -> None:
        for entry in self.users:
            if entry.user.id == user_id:
                object.__setattr__(entry, "password_hash", password_hash)
                return


@dataclass
class FakePasswordResetRepo(IPasswordResetRepository):
    codes: list[PasswordResetCode] = field(default_factory=list)

    def create(
        self,
        user_id: UUID,
        code_hash: str,
        expires_at: datetime,
    ) -> PasswordResetCode:
        record = PasswordResetCode(
            id=uuid4(),
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            used=False,
            attempts=0,
            created_at=datetime.now(timezone.utc),
        )
        self.codes.append(record)
        return record

    def get_latest_for_user(self, user_id: UUID) -> PasswordResetCode | None:
        matching = [c for c in self.codes if c.user_id == user_id]
        return matching[-1] if matching else None

    def get_by_id(self, code_id: UUID) -> PasswordResetCode | None:
        for c in self.codes:
            if c.id == code_id:
                return c
        return None

    def increment_attempts(self, code_id: UUID) -> None:
        for c in self.codes:
            if c.id == code_id:
                object.__setattr__(c, "attempts", c.attempts + 1)
                return

    def mark_used(self, code_id: UUID) -> None:
        for c in self.codes:
            if c.id == code_id:
                object.__setattr__(c, "used", True)
                return

    def invalidate_all_for_user(self, user_id: UUID) -> None:
        for c in self.codes:
            if c.user_id == user_id:
                object.__setattr__(c, "used", True)


@dataclass
class FakeEmailSender(IEmailSender):
    sent: list[dict] = field(default_factory=list)

    def send_password_reset_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        self.sent.append(
            {
                "to_email": to_email,
                "to_name": to_name,
                "code": code,
                "expires_minutes": expires_minutes,
            }
        )


def _build_service(
    reset_expire_minutes: int = 15,
) -> tuple[AuthService, FakeUserRepo, FakePasswordResetRepo, FakeEmailSender]:
    users = FakeUserRepo()
    resets = FakePasswordResetRepo()
    email = FakeEmailSender()
    svc = AuthService(
        users=users,
        password_resets=resets,
        email_sender=email,
        reset_expire_minutes=reset_expire_minutes,
    )
    return svc, users, resets, email


# ---------------------------------------------------------------------------
# Existing register / login tests (preserved)
# ---------------------------------------------------------------------------


def test_register_and_login() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    user, _tok = auth.register(
        email="alice@gmail.com",
        password="secret12",
        first_name="Alice",
        last_name="B",
        level="2e",
    )
    assert user.email == "alice@gmail.com"
    u2, _tok2 = auth.login("alice@gmail.com", "secret12")
    assert u2.id == user.id


def test_register_duplicate() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    auth.register(
        email="alice@gmail.com",
        password="secret12",
        first_name="Alice",
        last_name="B",
        level="2e",
    )
    with pytest.raises(AuthError) as exc:
        auth.register(
            email="alice@gmail.com",
            password="other",
            first_name="C",
            last_name="D",
            level="2e",
        )
    assert exc.value.code == "email_taken"


def test_login_wrong_password() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    auth.register(
        email="alice@gmail.com",
        password="rightpass",
        first_name="Alice",
        last_name="B",
        level="2e",
    )
    with pytest.raises(AuthError):
        auth.login("alice@gmail.com", "wrong")


# ---------------------------------------------------------------------------
# Email validation tests (offline-safe — syntax + disposable only)
# ---------------------------------------------------------------------------


def test_register_rejects_invalid_email_syntax() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    with pytest.raises(AuthError) as exc:
        auth.register(
            email="not-an-email",
            password="secret12",
            first_name="A",
            last_name="B",
            level="2e",
        )
    assert exc.value.code == "invalid_email"


def test_register_rejects_disposable_domain() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    with pytest.raises(AuthError) as exc:
        auth.register(
            email="user@mailinator.com",
            password="secret12",
            first_name="A",
            last_name="B",
            level="2e",
        )
    assert exc.value.code == "invalid_email"


# ---------------------------------------------------------------------------
# Forgot-password happy path
# ---------------------------------------------------------------------------


def test_request_password_reset_sends_email() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("secret"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")

    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["to_email"] == "alice@gmail.com"
    assert len(email_sender.sent[0]["code"]) == 6
    assert email_sender.sent[0]["code"].isdigit()


def test_request_password_reset_unknown_email_is_silent() -> None:
    svc, _users, _resets, email_sender = _build_service()
    svc.request_password_reset("unknown@gmail.com")
    assert len(email_sender.sent) == 0


def test_verify_and_reset_password_happy_path() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("oldpass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    raw_code = email_sender.sent[0]["code"]

    reset_token = svc.verify_reset_code("alice@gmail.com", raw_code)
    assert isinstance(reset_token, str) and len(reset_token) > 0

    svc.reset_password(reset_token, "newpassword123")

    with pytest.raises(AuthError) as exc:
        svc.login("alice@gmail.com", "oldpass")
    assert exc.value.code == "invalid_credentials"

    user, _tok = svc.login("alice@gmail.com", "newpassword123")
    assert user.email == "alice@gmail.com"


def test_verify_reset_code_wrong_code_increments_attempts() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("pass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    record = resets.get_latest_for_user(users.get_by_email("alice@gmail.com").user.id)  # type: ignore[union-attr]

    with pytest.raises(AuthError) as exc:
        svc.verify_reset_code("alice@gmail.com", "000000")
    assert exc.value.code == "invalid_code"

    updated = resets.get_by_id(record.id)
    assert updated is not None
    assert updated.attempts == 1


def test_verify_reset_code_expired() -> None:
    svc, users, resets, _email = _build_service(reset_expire_minutes=15)
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("pass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    user_id = users.get_by_email("alice@gmail.com").user.id  # type: ignore[union-attr]
    record = resets.get_latest_for_user(user_id)
    assert record is not None
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    object.__setattr__(record, "expires_at", expired_at)

    _email_sender_ref = FakeEmailSender()
    raw_code = _email_sender_ref.sent[0]["code"] if _email_sender_ref.sent else "123456"

    with pytest.raises(AuthError) as exc:
        svc.verify_reset_code("alice@gmail.com", raw_code)
    assert exc.value.code == "invalid_code"


def test_verify_reset_code_too_many_attempts() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("pass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    user_id = users.get_by_email("alice@gmail.com").user.id  # type: ignore[union-attr]
    record = resets.get_latest_for_user(user_id)
    assert record is not None
    object.__setattr__(record, "attempts", 5)

    with pytest.raises(AuthError) as exc:
        svc.verify_reset_code("alice@gmail.com", "000000")
    assert exc.value.code == "too_many_attempts"


def test_reset_password_code_invalidated_after_use() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("oldpass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    raw_code = email_sender.sent[0]["code"]

    reset_token = svc.verify_reset_code("alice@gmail.com", raw_code)
    svc.reset_password(reset_token, "newpassword123")

    with pytest.raises(AuthError) as exc:
        svc.reset_password(reset_token, "anotherpass456")
    assert exc.value.code == "invalid_token"


def test_request_password_reset_invalidates_previous_code() -> None:
    svc, users, resets, email_sender = _build_service()
    users.create_user(
        email="alice@gmail.com",
        password_hash=hash_password("pass"),
        first_name="Alice",
        last_name="B",
        level="2e",
    )

    svc.request_password_reset("alice@gmail.com")
    first_code = email_sender.sent[0]["code"]

    svc.request_password_reset("alice@gmail.com")
    second_code = email_sender.sent[1]["code"]

    with pytest.raises(AuthError) as exc:
        svc.verify_reset_code("alice@gmail.com", first_code)
    assert exc.value.code in ("invalid_code",)

    reset_token = svc.verify_reset_code("alice@gmail.com", second_code)
    assert reset_token
