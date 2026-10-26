import base64
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from fastapi.encoders import jsonable_encoder
from app.auth.dependencies import get_auth_context
from sqlalchemy.orm import Session

from app.auth.dependencies import require_org_role
from app.core.config import get_settings
from app.core.db import get_db
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, ExtractedFact, Finding, GuidelineUpdateSuggestion, Invite, Membership, Notification, Organization, Review, Rule, Scan, SourcePassage, VerificationDecision
from app.core.rate_limit import client_ip, enforce_rate_limit
from app.storage.factory import get_storage

router = APIRouter(tags=["organisation-settings"])


class WorkspaceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    llm_processing_allowed: bool


class NotificationPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    in_app: bool
    email: bool


class RetentionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retention_days: int = Field(ge=30, le=3650)


class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation_name: str = Field(min_length=2, max_length=180)


@router.patch("/orgs/{organization_id}/settings")
def update_workspace_settings(organization_id: str, payload: WorkspaceSettings, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    if payload.llm_processing_allowed and not get_settings().allow_workspace_llm:
        raise HTTPException(status_code=409, detail="No approved AI provider is configured for this deployment yet.")
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    organization.llm_processing_allowed = payload.llm_processing_allowed
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="organization.ai_processing_setting_changed", entity_type="organization", entity_id=organization_id, details={"allowed": payload.llm_processing_allowed}))
    db.commit()
    return {"llm_processing_allowed": organization.llm_processing_allowed, "provider": get_settings().llm_provider if organization.llm_processing_allowed else None}


@router.get("/orgs/{organization_id}/notification-preferences")
def get_notification_preferences(organization_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    membership = db.query(Membership).filter_by(organization_id=organization_id, user_id=context.user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return membership.notification_preferences or {"in_app": True, "email": True}


@router.patch("/orgs/{organization_id}/notification-preferences")
def update_notification_preferences(organization_id: str, payload: NotificationPreferences, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    membership = db.query(Membership).filter_by(organization_id=organization_id, user_id=context.user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    membership.notification_preferences = payload.model_dump()
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=context.user.id, action="membership.notification_preferences_changed", entity_type="membership", entity_id=membership.id, details={"in_app": payload.in_app, "email": payload.email}))
    db.commit()
    return membership.notification_preferences


@router.get("/orgs/{organization_id}/retention-settings")
def get_retention_settings(organization_id: str, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    organization = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not organization:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return {"retention_days": organization.retention_days, "scope": "completed scan and finding history"}


@router.patch("/orgs/{organization_id}/retention-settings")
def update_retention_settings(organization_id: str, payload: RetentionSettings, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    organization = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not organization:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    organization.retention_days = payload.retention_days
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="organization.retention_setting_changed", entity_type="organization", entity_id=organization_id, details={"retention_days": payload.retention_days, "scope": "completed scan and finding history"}))
    db.commit()
    return {"retention_days": organization.retention_days, "scope": "completed scan and finding history"}


@router.get("/orgs/{organization_id}/data-export")
def export_organization_data(organization_id: str, request: Request, membership: Membership = Depends(require_org_role("admin", allow_unapproved=True)), db: Session = Depends(get_db)):
    enforce_rate_limit(f"data-export:{organization_id}:{membership.user_id}:{client_ip(request)}", limit=3, window_seconds=3600)
    organization = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not organization:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    models = [Membership, Invite, BrandGuidelineSource, SourcePassage, Rule, Campaign, Asset, ExtractedFact, Scan, Finding, Review, GuidelineUpdateSuggestion, Notification, VerificationDecision, AuditEvent]
    export = {"organization": jsonable_encoder(organization), "exported_at": datetime.now(UTC).isoformat(), "records": {}}
    total_bytes = 0
    for model in models:
        rows = db.scalars(select(model).where(model.organization_id == organization_id)).all()
        export["records"][model.__tablename__] = [jsonable_encoder(row) for row in rows]
        if model is Invite:
            for item in export["records"][model.__tablename__]:
                item.pop("code_hash", None)
        if model in {Asset, BrandGuidelineSource}:
            for index, row in enumerate(rows):
                object_key = row.file_ref if model is Asset else row.document_ref
                if not object_key:
                    continue
                try:
                    chunks, _content_type = get_storage().stream(organization_id, object_key)
                    contents = b"".join(chunks)
                except OSError:
                    continue
                total_bytes += len(contents)
                if total_bytes > 100 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="The export exceeds the 100 MB download limit. Export smaller workspaces separately.")
                export["records"][model.__tablename__][index]["original_file_base64"] = base64.b64encode(contents).decode("ascii")
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="organization.data_exported", entity_type="organization", entity_id=organization_id, details={"file_bytes": total_bytes}))
    db.commit()
    response = JSONResponse(content=jsonable_encoder(export))
    response.headers["Content-Disposition"] = f'attachment; filename="brandlens-{organization_id}-export.json"'
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/orgs/{organization_id}/data-deletion", status_code=202)
def delete_organization_data(organization_id: str, payload: DeletionRequest, request: Request, membership: Membership = Depends(require_org_role("admin", allow_unapproved=True)), db: Session = Depends(get_db)):
    enforce_rate_limit(f"data-deletion:{organization_id}:{membership.user_id}:{client_ip(request)}", limit=2, window_seconds=86400)
    organization = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)).with_for_update())
    if not organization:
        return {"status": "deleted"}
    if organization.is_sample:
        raise HTTPException(status_code=409, detail="The read-only sample workspace cannot be deleted.")
    if payload.confirmation_name != organization.name:
        raise HTTPException(status_code=422, detail="Type the organisation name exactly to confirm deletion.")
    storage = get_storage()
    assets = db.scalars(select(Asset).where(Asset.organization_id == organization_id)).all()
    sources = db.scalars(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == organization_id)).all()
    for asset in assets:
        if asset.file_ref:
            storage.delete(organization_id, asset.file_ref)
    for source in sources:
        if source.document_ref:
            storage.delete(organization_id, source.document_ref)
    for asset in assets:
        asset.supersedes_asset_id = None
    db.flush()
    for model in (Review, Finding, ExtractedFact, Scan, Asset, Rule, SourcePassage, BrandGuidelineSource, GuidelineUpdateSuggestion, Notification, Invite, VerificationDecision, Campaign, Membership):
        db.execute(delete(model).where(model.organization_id == organization_id))
    organization.deleted_at = datetime.now(UTC)
    organization.llm_processing_allowed = False
    organization.name = "Deleted organisation"
    organization.industry = "Deleted"
    organization.official_email = f"deleted+{organization.id}@example.invalid"
    organization.website = "https://example.invalid"
    organization.contact_person = "Deleted"
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="organization.data_deleted", entity_type="organization", entity_id=organization_id, details={"content_removed": True, "audit_history_retained": True}))
    db.commit()
    return {"status": "deleted", "audit_history_retained": True}
