from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing_extensions import Annotated

Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
SafeName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictInput):
    email: EmailStr
    password: Password
    display_name: SafeName
    recovery_question: Literal["first_school", "birth_city", "first_pet"]
    recovery_answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]


class LoginRequest(StrictInput):
    # Login must accept development-only addresses such as the bootstrap admin's .local email.
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class PasswordResetRequest(StrictInput):
    email: EmailStr


class PasswordResetConfirm(StrictInput):
    token: Annotated[str, Field(min_length=20, max_length=200)]
    password: Password


class RecoveryPasswordReset(StrictInput):
    email: EmailStr
    recovery_question: Literal["first_school", "birth_city", "first_pet"]
    recovery_answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    password: Password


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    display_name: str
    email_verified_at: datetime | None


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    expires_at: datetime
    current: bool


class OrganizationSummary(BaseModel):
    id: str
    name: str
    industry: str
    verification_status: str
    role: Literal["admin", "creator", "reviewer"]
