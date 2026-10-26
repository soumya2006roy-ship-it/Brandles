from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint
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
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    notification_preferences: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False, default=lambda: {"in_app": True, "email": True})
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
    __table_args__ = (
        UniqueConstraint("organization_id", "family_id", "version", name="uq_source_family_version"),
        UniqueConstraint("organization_id", "id", name="uq_source_org_id"),
        CheckConstraint("status IN ('draft','approved','archived')", name="ck_sources_status"),
        CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_source_effective_window"),
        Index("ix_sources_org_status", "organization_id", "status"),
        Index("ix_sources_org_family", "organization_id", "family_id", "version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    document_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(240), nullable=False, default="source-document")
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    effective_from: Mapped[date | None] = mapped_column(Date())
    effective_to: Mapped[date | None] = mapped_column(Date())
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourcePassage(Base):
    __tablename__ = "source_passages"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_source_passage_org_id"),
        ForeignKeyConstraint(["organization_id", "source_id"], ["brand_guideline_sources.organization_id", "brand_guideline_sources.id"], ondelete="CASCADE", name="fk_passage_source_tenant"),
        Index("ix_source_passages_org_source", "organization_id", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    location_label: Mapped[str | None] = mapped_column(String(120))
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536).with_variant(JSON(), "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        CheckConstraint("status IN ('draft','suggested','active','archived','rejected')", name="ck_rules_status"),
        CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_rules_valid_window"),
        ForeignKeyConstraint(["organization_id", "source_passage_id"], ["source_passages.organization_id", "source_passages.id"], ondelete="RESTRICT", name="fk_rule_passage_tenant"),
        Index("ix_rules_org_status_channel", "organization_id", "status", "channel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    channel: Mapped[str | None] = mapped_column(String(50))
    valid_from: Mapped[date | None] = mapped_column(Date())
    valid_to: Mapped[date | None] = mapped_column(Date())
    source_passage_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_campaign_org_id"),
        CheckConstraint("ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at", name="ck_campaign_date_window"),
        Index("ix_campaigns_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    starts_at: Mapped[date | None] = mapped_column(Date())
    ends_at: Mapped[date | None] = mapped_column(Date())
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    planned_publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_asset_org_id"),
        UniqueConstraint("organization_id", "campaign_id", "asset_group_id", "version", name="uq_asset_group_version"),
        ForeignKeyConstraint(["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"], ondelete="CASCADE", name="fk_asset_campaign_tenant"),
        ForeignKeyConstraint(["organization_id", "supersedes_asset_id"], ["assets.organization_id", "assets.id"], ondelete="RESTRICT", name="fk_asset_supersedes_tenant"),
        CheckConstraint("asset_type IN ('text','image','document')", name="ck_assets_type"),
        CheckConstraint("version > 0 AND size_bytes >= 0", name="ck_asset_version_size"),
        CheckConstraint("malware_status IN ('not_configured','not_applicable','clean')", name="ck_asset_malware_status"),
        CheckConstraint("extraction_status IN ('complete','not_required','not_configured','unavailable','failed')", name="ck_asset_extraction_status"),
        Index("ix_assets_org_campaign", "organization_id", "campaign_id"),
        Index("ix_assets_org_group_current", "organization_id", "asset_group_id", "current"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    asset_group_id: Mapped[str] = mapped_column(String(36), nullable=False, default=new_id)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supersedes_asset_id: Mapped[str | None] = mapped_column(String(36))
    file_ref: Mapped[str | None] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(240))
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="text/plain")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    malware_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_configured")
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_required")
    metadata_stripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_content: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    logo_matches: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
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
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_scan_org_id"),
        ForeignKeyConstraint(["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"], ondelete="CASCADE", name="fk_scan_campaign_tenant"),
        ForeignKeyConstraint(["organization_id", "asset_id"], ["assets.organization_id", "assets.id"], ondelete="CASCADE", name="fk_scan_asset_tenant"),
        Index("ix_scans_org_campaign_created", "organization_id", "campaign_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(String(36))
    asset_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    model_version: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    rules_version: Mapped[str | None] = mapped_column(String(80))
    asset_versions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_asset_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    llm_vendor: Mapped[str | None] = mapped_column(String(80))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_finding_org_id"),
        ForeignKeyConstraint(["organization_id", "scan_id"], ["scans.organization_id", "scans.id"], ondelete="CASCADE", name="fk_finding_scan_tenant"),
        ForeignKeyConstraint(["organization_id", "asset_id"], ["assets.organization_id", "assets.id"], ondelete="CASCADE", name="fk_finding_asset_tenant"),
        ForeignKeyConstraint(["organization_id", "source_passage_id"], ["source_passages.organization_id", "source_passages.id"], ondelete="RESTRICT", name="fk_finding_passage_tenant"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_findings_confidence"),
        Index("ix_findings_org_scan_status", "organization_id", "scan_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    scan_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(36))
    finding_type: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    flagged_region: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id", ondelete="SET NULL"))
    source_passage_id: Mapped[str | None] = mapped_column(String(36))
    quoted_excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None]
    suggested_fix: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    dismissal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("(finding_id IS NOT NULL) != (asset_id IS NOT NULL)", name="ck_reviews_target_xor"),
        ForeignKeyConstraint(["organization_id", "asset_id"], ["assets.organization_id", "assets.id"], ondelete="CASCADE", name="fk_review_asset_tenant"),
        ForeignKeyConstraint(["organization_id", "scan_id"], ["scans.organization_id", "scans.id"], ondelete="CASCADE", name="fk_review_scan_tenant"),
        Index("ix_reviews_org_created", "organization_id", "created_at"),
        Index("ix_reviews_submission_id", "submission_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    asset_version: Mapped[int | None] = mapped_column(Integer)
    submission_id: Mapped[str | None] = mapped_column(String(36))
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    submitted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    scan_id: Mapped[str | None] = mapped_column(String(36))
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class GuidelineUpdateSuggestion(Base):
    __tablename__ = "guideline_update_suggestions"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "source_id"], ["brand_guideline_sources.organization_id", "brand_guideline_sources.id"], ondelete="RESTRICT", name="fk_guideline_suggestion_source_tenant"),
        Index("ix_guideline_suggestions_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(36))
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
