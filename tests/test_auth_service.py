"""Unit tests for AuthService with in-memory fakes (no database)."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.auth_service import AuthError, AuthService
from app.domain.entities import User, UserWithHash
from app.domain.ports import IUserRepository


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

    def get_by_id(self, user_id):
        for u in self.users:
            if u.user.id == user_id:
                return u.user
        return None


def test_register_and_login() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    user, _tok = auth.register(
        email="a@b.com",
        password="secret12",
        first_name="A",
        last_name="B",
        level="2e",
    )
    assert user.email == "a@b.com"
    u2, _tok2 = auth.login("a@b.com", "secret12")
    assert u2.id == user.id


def test_register_duplicate() -> None:
    repo = FakeUserRepo()
    auth = AuthService(repo)
    auth.register(
        email="a@b.com",
        password="secret12",
        first_name="A",
        last_name="B",
        level="2e",
    )
    with pytest.raises(AuthError) as exc:
        auth.register(
            email="a@b.com",
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
        email="a@b.com",
        password="rightpass",
        first_name="A",
        last_name="B",
        level="2e",
    )
    with pytest.raises(AuthError):
        auth.login("a@b.com", "wrong")
