from datetime import UTC, datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_auth_context, get_current_user, require_org_role, require_platform_admin
from app.auth.schemas import OrganizationSummary
from app.core.db import get_db
from app.core.rate_limit import enforce_rate_limit
from app.core.security import as_utc, digest_secret
from app.db.models import AuditEvent, Invite, Membership, Organization, User, VerificationDecision
from app.orgs.schemas import InviteCreate, InviteRedeem, InviteResponse, InviteSummary, OrganizationCreate, OrganizationResponse, VerificationDecisionRequest, VerificationHistoryItem

router = APIRouter(tags=["organisations"])


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_invite_code() -> str:
    return f"BL-{secrets.token_urlsafe(32)}"


def get_member(organization_id: str, user_id: str, db: Session) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.user_id == user_id))
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return membership


@router.get("/orgs", response_model=list[OrganizationSummary])
def list_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Organization, Membership.role).join(Membership, Membership.organization_id == Organization.id).where(Membership.user_id == user.id, Organization.deleted_at.is_(None)).order_by(Organization.created_at.desc())).all()
    return [OrganizationSummary(id=org.id, name=org.name, industry=org.industry, verification_status=org.verification_status, role=role) for org, role in rows]


@router.post("/orgs", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    host = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"create-org:{user.id}:{host}", limit=3, window_seconds=3600)
    org = Organization(
        name=payload.name,
        industry=payload.industry.strip(),
        official_email=str(payload.official_email).strip().lower(),
        website=str(payload.website),
        contact_person=payload.contact_person,
        verification_status="pending_verification",
        created_by=user.id,
    )
    db.add(org)
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role="admin"))
    db.add(AuditEvent(organization_id=org.id, actor_user_id=user.id, action="organization.submitted_for_verification", entity_type="organization", entity_id=org.id, details={"status": "pending_verification"}))
    db.commit()
    db.refresh(org)
    return org


@router.get("/orgs/{organization_id}", response_model=OrganizationResponse)
def get_organization(organization_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    get_member(organization_id, context.user.id, db)
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return org


@router.post("/orgs/{organization_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(payload: InviteCreate, organization_id: str, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    code = new_invite_code()
    invite = Invite(organization_id=organization_id, code_hash=digest_secret(code), role=payload.role, expires_at=now_utc() + timedelta(days=payload.expires_in_days), usage_limit=payload.usage_limit, created_by=membership.user_id)
    db.add(invite)
    db.flush()
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="invite.created", entity_type="invite", entity_id=invite.id, details={"role": payload.role, "usage_limit": payload.usage_limit}))
    db.commit()
    db.refresh(invite)
    return InviteResponse(id=invite.id, code=code, role=invite.role, expires_at=invite.expires_at, usage_limit=invite.usage_limit)


@router.get("/orgs/{organization_id}/invites", response_model=list[InviteSummary])
def list_invites(organization_id: str, _: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Invite).where(Invite.organization_id == organization_id).order_by(Invite.created_at.desc())).all()
    return rows


@router.delete("/orgs/{organization_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(organization_id: str, invite_id: str, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    invite = db.scalar(select(Invite).where(Invite.organization_id == organization_id, Invite.id == invite_id).with_for_update())
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found.")
    if not invite.revoked_at:
        invite.revoked_at = now_utc()
        db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="invite.revoked", entity_type="invite", entity_id=invite.id))
        db.commit()


@router.post("/orgs/{organization_id}/invites/{invite_id}/regenerate", response_model=InviteResponse)
def regenerate_invite(organization_id: str, invite_id: str, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    old = db.scalar(select(Invite).where(Invite.organization_id == organization_id, Invite.id == invite_id).with_for_update())
    if not old:
        raise HTTPException(status_code=404, detail="Invite not found.")
    if old.revoked_at:
        raise HTTPException(status_code=409, detail="A revoked invite cannot be regenerated.")
    old.revoked_at = now_utc()
    code = new_invite_code()
    replacement = Invite(organization_id=organization_id, code_hash=digest_secret(code), role=old.role, expires_at=now_utc() + timedelta(days=7), usage_limit=old.usage_limit, created_by=membership.user_id)
    db.add(replacement)
    db.flush()
    db.add(AuditEvent(organization_id=organization_id, actor_user_id=membership.user_id, action="invite.regenerated", entity_type="invite", entity_id=replacement.id, details={"replaces": old.id}))
    db.commit()
    db.refresh(replacement)
    return InviteResponse(id=replacement.id, code=code, role=replacement.role, expires_at=replacement.expires_at, usage_limit=replacement.usage_limit)


@router.post("/invites/redeem", status_code=status.HTTP_201_CREATED)
def redeem_invite(payload: InviteRedeem, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    host = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"redeem-invite:{user.id}:{host}", limit=10, window_seconds=3600)
    invite = db.scalar(select(Invite).where(Invite.code_hash == digest_secret(payload.code)).with_for_update())
    if not invite or invite.revoked_at or as_utc(invite.expires_at) <= now_utc() or invite.usage_count >= invite.usage_limit:
        raise HTTPException(status_code=400, detail="This invite code is invalid, expired or already used.")
    org = db.scalar(select(Organization).where(Organization.id == invite.organization_id, Organization.deleted_at.is_(None)))
    if not org or org.verification_status != "approved":
        raise HTTPException(status_code=423, detail="This organisation cannot accept members yet.")
    if db.scalar(select(Membership.id).where(Membership.organization_id == org.id, Membership.user_id == user.id)):
        raise HTTPException(status_code=409, detail="You already belong to this organisation.")
    invite.usage_count += 1
    membership = Membership(organization_id=org.id, user_id=user.id, role=invite.role)
    db.add(membership)
    db.flush()
    db.add(AuditEvent(organization_id=org.id, actor_user_id=user.id, action="invite.redeemed", entity_type="membership", entity_id=membership.id, details={"role": invite.role}))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already belong to this organisation.") from None
    return {"message": "You joined the organisation.", "organization_id": org.id, "role": invite.role}


@router.get("/platform/verifications", response_model=list[OrganizationResponse])
def verification_queue(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    return db.scalars(select(Organization).where(Organization.verification_status.in_(["pending_verification", "more_information_required"]), Organization.deleted_at.is_(None)).order_by(Organization.created_at.asc())).all()


@router.get("/platform/verifications/{organization_id}/history", response_model=list[VerificationHistoryItem])
def verification_history(organization_id: str, _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(VerificationDecision, User.display_name).join(User, User.id == VerificationDecision.actor_user_id).where(VerificationDecision.organization_id == organization_id).order_by(VerificationDecision.created_at.desc())).all()
    if not db.get(Organization, organization_id):
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return [VerificationHistoryItem(id=decision.id, decision=decision.decision, note=decision.note, actor_name=name, created_at=decision.created_at) for decision, name in rows]


@router.post("/platform/verifications/{organization_id}/decision", response_model=OrganizationResponse)
def decide_verification(organization_id: str, payload: VerificationDecisionRequest, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)).with_for_update())
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    if org.verification_status not in {"pending_verification", "more_information_required"}:
        raise HTTPException(status_code=409, detail="This organisation is not awaiting verification.")
    if org.created_by == admin.id:
        raise HTTPException(status_code=403, detail="A platform administrator cannot verify an organisation they submitted.")
    if payload.decision in {"rejected", "more_information_required"} and not (payload.note and payload.note.strip()):
        raise HTTPException(status_code=422, detail="Add a note explaining this decision.")
    org.verification_status = payload.decision
    db.add(VerificationDecision(organization_id=org.id, actor_user_id=admin.id, decision=payload.decision, note=payload.note.strip() if payload.note else None))
    db.add(AuditEvent(organization_id=org.id, actor_user_id=admin.id, action=f"organization.verification.{payload.decision}", entity_type="organization", entity_id=org.id, details={"status": payload.decision}))
    db.commit()
    db.refresh(org)
    return org


