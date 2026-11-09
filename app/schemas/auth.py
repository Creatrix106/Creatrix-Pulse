from typing import Annotated, Literal

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, Field, StringConstraints, field_validator

from app.schemas.common import CamelModel

UserRole = Literal["admin", "analyst", "viewer"]


def _normalise_email(value: str) -> str:
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError("Enter a valid email address.") from None


Email = Annotated[str, AfterValidator(_normalise_email)]


class LoginIn(CamelModel):
    email: Email
    # Do not reveal the password policy on login: a wrong/short password is simply a failed login.
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class RegisterIn(CamelModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True)]
    email: Email
    password: Annotated[str, Field(max_length=1024)]

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("Enter your full name.")
        if len(value) > 120:
            raise ValueError("Name must be at most 120 characters.")
        return value

    # Same rules as the frontend's registerSchema (features/auth/schemas.ts); the server is the source of truth.
    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Include at least one number.")
        return value


class UserOut(CamelModel):
    id: str
    name: str
    email: str
    role: UserRole
