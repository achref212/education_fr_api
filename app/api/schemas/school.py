from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import School


class SchoolCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=512)
    email: EmailStr
    address: str | None = None
    city: str | None = None
    postalCode: str | None = Field(default=None, alias="postalCode")
    phone: str | None = None
    directorName: str | None = Field(default=None, alias="directorName")


class SchoolProfileUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=512)
    address: str | None = None
    city: str | None = None
    postalCode: str | None = Field(default=None, alias="postalCode")
    phone: str | None = None
    directorName: str | None = Field(default=None, alias="directorName")


class SchoolUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=512)
    address: str | None = None
    city: str | None = None
    postalCode: str | None = Field(default=None, alias="postalCode")
    phone: str | None = None
    directorName: str | None = Field(default=None, alias="directorName")
    isActive: bool | None = Field(default=None, alias="isActive")


class SchoolPublicOut(BaseModel):
    """Minimal school info exposed during student registration."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    city: str | None = None

    @classmethod
    def from_domain(cls, s: School) -> "SchoolPublicOut":
        return cls(id=s.id, name=s.name, city=s.city)


class SchoolOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    email: str
    isActive: bool
    mustChangePassword: bool = False
    createdAt: datetime
    address: str | None = None
    city: str | None = None
    postalCode: str | None = None
    phone: str | None = None
    directorName: str | None = None
    createdByAdminId: UUID | None = None

    @classmethod
    def from_domain(cls, s: School) -> "SchoolOut":
        return cls(
            id=s.id,
            name=s.name,
            email=s.email,
            isActive=s.is_active,
            mustChangePassword=s.must_change_password,
            createdAt=s.created_at,
            address=s.address,
            city=s.city,
            postalCode=s.postal_code,
            phone=s.phone,
            directorName=s.director_name,
            createdByAdminId=s.created_by_admin_id,
        )


class SchoolCreateOut(BaseModel):
    """Response when a school is created — includes the plain-text password (shown once)."""

    model_config = ConfigDict(populate_by_name=True)

    school: SchoolOut
    plainPassword: str

    @classmethod
    def from_domain(cls, school: School, plain_password: str) -> "SchoolCreateOut":
        return cls(school=SchoolOut.from_domain(school), plainPassword=plain_password)


class SchoolTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "school"
    school: SchoolOut


class ProfCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    firstName: str = Field(min_length=1, max_length=255)
    lastName: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = None
    dateOfBirth: date | None = None


class ProfCreateOut(BaseModel):
    """Response when a professor is created — includes the plain-text password (shown once)."""

    model_config = ConfigDict(populate_by_name=True)

    userId: UUID
    firstName: str
    lastName: str
    email: str
    plainPassword: str
    phone: str | None = None
    dateOfBirth: date | None = None
