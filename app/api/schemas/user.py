import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import User

_RESET_CODE_PATTERN = re.compile(r"^\d{6}$")

CLASS_LEVELS = ["2e", "3e", "4e", "5e", "6e", "7e", "8e", "9e"]


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
    classLevel: str | None = None
    schoolId: UUID | None = None
    teacherSchoolId: UUID | None = None
    phone: str | None = None
    dateOfBirth: date | None = None

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
            classLevel=u.class_level,
            schoolId=u.school_id,
            teacherSchoolId=u.teacher_school_id,
            phone=u.phone,
            dateOfBirth=u.date_of_birth,
        )


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    firstName: str
    lastName: str
    level: str
    classLevel: str | None = None
    schoolId: UUID | None = None
    phone: str | None = None
    dateOfBirth: date | None = None


class RegisterOut(BaseModel):
    message: str
    registration_state_token: str


class VerifyRegistrationIn(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    registration_state_token: str


class ResendActivationIn(BaseModel):
    email: EmailStr


class ResendActivationOut(BaseModel):
    message: str
    registration_state_token: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserOut | None = None


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ForgotPasswordOut(BaseModel):
    message: str
    reset_state_token: str | None = None


class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    reset_state_token: str


class ResetTokenResponse(BaseModel):
    reset_token: str


class ResetPasswordIn(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(min_length=6)


class MessageResponse(BaseModel):
    message: str
