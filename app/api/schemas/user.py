import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import User

_RESET_CODE_PATTERN = re.compile(r"^\d{6}$")


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


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class ResetTokenResponse(BaseModel):
    reset_token: str


class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=6)


class MessageResponse(BaseModel):
    message: str
