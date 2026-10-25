from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email_normalized", name="uq_users_email_normalized"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class PlatformAdmin(Base):
    __tablename__ = "platform_admins"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    granted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("verification_status IN ('draft','pending_verification','approved','rejected','more_information_required')", name="ck_organizations_verification_status"),
        Index("ix_organizations_verification_status", "verification_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    official_email: Mapped[str] = mapped_column(String(320), nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(120), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_verification")
    llm_processing_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        CheckConstraint("role IN ('admin','creator','reviewer')", name="ck_memberships_role"),
        Index("ix_memberships_user_org", "user_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_invites_code_hash"),
        CheckConstraint("role IN ('admin','creator','reviewer')", name="ck_invites_role"),
        CheckConstraint("usage_limit > 0 AND usage_count >= 0 AND usage_count <= usage_limit", name="ck_invites_usage"),
        Index("ix_invites_org_status_expiry", "organization_id", "revoked_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usage_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    __table_args__ = (CheckConstraint("purpose IN ('email_verification','password_reset')", name="ck_auth_tokens_purpose"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_expiry", "user_id", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationDecision(Base):
    __tablename__ = "verification_decisions"
    __table_args__ = (CheckConstraint("decision IN ('approved','rejected','more_information_required')", name="ck_verification_decisions_decision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_org_created", "organization_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class BrandGuidelineSource(Base):
    __tablename__ = "brand_guideline_sources"
    __table_args__ = (UniqueConstraint("organization_id", "version", name="uq_source_org_version"), Index("ix_sources_org_status", "organization_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    document_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourcePassage(Base):
    __tablename__ = "source_passages"
    __table_args__ = (Index("ix_source_passages_org_source", "organization_id", "source_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("brand_guideline_sources.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536).with_variant(JSON(), "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (CheckConstraint("status IN ('draft','active','archived')", name="ck_rules_status"), Index("ix_rules_org_status_channel", "organization_id", "status", "channel"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    channel: Mapped[str | None] = mapped_column(String(50))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_passage_id: Mapped[str | None] = mapped_column(ForeignKey("source_passages.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_campaign_org_id"), Index("ix_campaigns_org_created", "organization_id", "created_at"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    planned_publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (ForeignKeyConstraint(["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"], ondelete="CASCADE", name="fk_asset_campaign_tenant"), Index("ix_assets_org_campaign", "organization_id", "campaign_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_ref: Mapped[str | None] = mapped_column(String(500))
    text_content: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    __table_args__ = (Index("ix_facts_org_campaign_type", "organization_id", "campaign_id", "fact_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    fact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    asset_location: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_passage_id: Mapped[str | None] = mapped_column(ForeignKey("source_passages.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_org_campaign_created", "organization_id", "campaign_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    model_version: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    rules_version: Mapped[str | None] = mapped_column(String(80))
    llm_vendor: Mapped[str | None] = mapped_column(String(80))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_findings_confidence"), Index("ix_findings_org_scan_status", "organization_id", "scan_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    finding_type: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    flagged_region: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id", ondelete="SET NULL"))
    source_passage_id: Mapped[str | None] = mapped_column(ForeignKey("source_passages.id", ondelete="SET NULL"))
    quoted_excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None]
    suggested_fix: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    dismissal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("(finding_id IS NOT NULL) != (asset_id IS NOT NULL)", name="ck_reviews_target_xor"), Index("ix_reviews_org_created", "organization_id", "created_at"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    asset_version: Mapped[int | None] = mapped_column(Integer)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class GuidelineUpdateSuggestion(Base):
    __tablename__ = "guideline_update_suggestions"
    __table_args__ = (Index("ix_guideline_suggestions_org_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("brand_guideline_sources.id", ondelete="SET NULL"))
    suggested_change: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_org_user_created", "organization_id", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
