from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_auth_context
from sqlalchemy.orm import Session

from app.auth.dependencies import require_org_role
from app.core.config import get_settings
from app.core.db import get_db
from app.db.models import AuditEvent, Membership, Organization

router = APIRouter(tags=["organisation-settings"])


class WorkspaceSettings(BaseModel):
    llm_processing_allowed: bool


class NotificationPreferences(BaseModel):
    in_app: bool
    email: bool


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
