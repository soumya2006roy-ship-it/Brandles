from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints
from typing_extensions import Annotated

OrgText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=180)]
OrgRole = Literal["admin", "creator", "reviewer"]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrganizationCreate(StrictInput):
    name: OrgText
    industry: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    official_email: EmailStr
    website: HttpUrl
    contact_person: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    industry: str
    official_email: EmailStr
    website: str
    contact_person: str
    verification_status: str
    llm_processing_allowed: bool
    created_at: datetime


class VerificationDecisionRequest(StrictInput):
    decision: Literal["approved", "rejected", "more_information_required"]
    note: Annotated[str | None, Field(max_length=1200)] = None


class VerificationHistoryItem(BaseModel):
    id: str
    decision: str
    note: str | None
    actor_name: str
    created_at: datetime


class AuditEventResponse(BaseModel):
    id: str
    actor_user_id: str | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str
    details: dict
    created_at: datetime


class InviteCreate(StrictInput):
    role: OrgRole
    expires_in_days: int = Field(default=7, ge=1, le=30)
    usage_limit: int = Field(default=1, ge=1, le=100)


class InviteResponse(BaseModel):
    id: str
    code: str
    role: str
    expires_at: datetime
    usage_limit: int


class InviteSummary(BaseModel):
    id: str
    role: str
    expires_at: datetime
    usage_limit: int
    usage_count: int
    revoked_at: datetime | None


class InviteRedeem(StrictInput):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=200)]
