from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import digest_secret
from app.db.models import Membership, Organization, PlatformAdmin, SessionRecord, User


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: SessionRecord


def get_auth_context(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    session_record = db.scalar(select(SessionRecord).where(
        SessionRecord.token_hash == digest_secret(raw_token),
        SessionRecord.revoked_at.is_(None),
        SessionRecord.expires_at > datetime.now(UTC),
    ))
    if not session_record:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    user = db.get(User, session_record.user_id)
    if not user or not user.is_active or not user.email_verified_at:
        raise HTTPException(status_code=401, detail="A verified account is required.")
    return AuthContext(user=user, session=session_record)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    return context.user


def require_platform_admin(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)) -> User:
    if not db.get(PlatformAdmin, context.user.id):
        raise HTTPException(status_code=403, detail="Platform administrator access is required.")
    return context.user


def require_org_role(*roles: str, allow_unapproved: bool = False) -> Callable:
    def dependency(request: Request, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)) -> Membership:
        organization_id = request.path_params.get("organization_id") or request.path_params.get("org_id")
        if not organization_id:
            raise HTTPException(status_code=404, detail="Organisation not found.")
        membership = db.scalar(select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == context.user.id,
        ))
        if not membership:
            raise HTTPException(status_code=404, detail="Organisation not found.")
        if membership.role not in roles:
            raise HTTPException(status_code=403, detail="Your organisation role cannot perform this action.")
        org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
        if not org:
            raise HTTPException(status_code=404, detail="Organisation not found.")
        if not allow_unapproved and org.verification_status != "approved":
            raise HTTPException(status_code=423, detail="This organisation is not approved for workspace actions.")
        return membership

    return dependency
