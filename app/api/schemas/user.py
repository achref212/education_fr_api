from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import User


class UserOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: str
    firstName: str
    lastName: str
    level: str
    createdAt: datetime
    role: str = "user"
    isActive: bool = True

    @classmethod
    def from_domain(cls, u: User) -> "UserOut":
        return cls(
            id=u.id,
            email=u.email,
            firstName=u.first_name,
            lastName=u.last_name,
            level=u.level,
            createdAt=u.created_at,
            role=u.role,
            isActive=u.is_active,
        )


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    firstName: str
    lastName: str
    level: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
