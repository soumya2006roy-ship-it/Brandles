from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath, PureWindowsPath
import secrets
from urllib.parse import quote

import pymupdf
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.auth.dependencies import get_auth_context, get_current_user, require_org_role, require_platform_admin
from app.auth.schemas import OrganizationSummary
from app.core.db import get_db
from app.core.mail import EmailSender, get_email_sender
from app.core.rate_limit import client_ip, enforce_rate_limit
from app.core.security import as_utc, digest_secret
from app.db.models import AuditEvent, Invite, Membership, Organization, OrganizationSubmission, PlatformAdmin, User, VerificationDecision
from app.assets.media import sniff_and_normalize
from app.notifications.service import record_notification, send_user_email
from app.orgs.schemas import AuditEventResponse, InviteCreate, InviteRedeem, InviteResponse, InviteSummary, OrganizationCreate, OrganizationResponse, OrganizationResubmit, OrganizationSubmissionResponse, VerificationDecisionRequest, VerificationHistoryItem
from app.sources.documents import identify_format
from app.storage.factory import get_storage
from app.storage.local import safe_filename

router = APIRouter(tags=["organisations"])
_AUDIT_PRIVATE_KEYS = {"question", "suggested_change", "comment", "note", "token", "secret", "code", "text", "excerpt", "content", "email", "document_text", "raw"}
MAX_ORGANIZATION_DOCUMENT_BYTES = 5 * 1024 * 1024


def organization_submission_openapi_extra(schema_name: str) -> dict:
    properties = {
        "name": {"type": "string"},
        "industry": {"type": "string"},
        "official_email": {"type": "string", "format": "email"},
        "website": {"type": "string", "format": "uri"},
        "contact_person": {"type": "string"},
        "document": {"type": "string", "format": "binary"},
    }
    if schema_name == "OrganizationResubmit":
        properties["note"] = {"type": "string", "maxLength": 1200}
    json_schema = {
        "type": "object",
        "properties": {key: value for key, value in properties.items() if key != "document"},
        "required": ["name", "industry", "official_email", "website", "contact_person"],
        "additionalProperties": False,
    }
    return {"requestBody": {"required": True, "content": {
        "application/json": {"schema": json_schema},
        "multipart/form-data": {"schema": {
            "type": "object",
            "properties": properties,
            "required": ["name", "industry", "official_email", "website", "contact_person"],
            "additionalProperties": False,
        }},
    }}}


def _safe_audit_details(value):
    if isinstance(value, dict):
        return {key: _safe_audit_details(item) for key, item in value.items() if key.casefold() not in _AUDIT_PRIVATE_KEYS}
    if isinstance(value, list):
        return [_safe_audit_details(item) for item in value]
    return value


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_invite_code() -> str:
    return f"BL-{secrets.token_urlsafe(32)}"


def get_member(organization_id: str, user_id: str, db: Session) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.user_id == user_id))
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return membership


async def parse_organization_request(request: Request, schema):
    content_type = request.headers.get("content-type", "").casefold()
    document = None
    if content_type.startswith("multipart/form-data"):
        form = await request.form(max_files=1, max_fields=10)
        allowed_fields = set(schema.model_fields) | {"document"}
        unexpected = set(form.keys()) - allowed_fields
        if unexpected:
            raise HTTPException(status_code=422, detail="The organisation form contains an unsupported field.")
        uploads = form.getlist("document")
        if len(uploads) > 1:
            raise HTTPException(status_code=422, detail="Upload one organisation document at a time.")
        if uploads and uploads[0].filename:
            if not isinstance(uploads[0], StarletteUploadFile):
                raise HTTPException(status_code=422, detail="The organisation document upload is invalid.")
            document = uploads[0]
        values = {key: form.get(key) for key in schema.model_fields}
    elif content_type.startswith("application/json"):
        values = await request.json()
    else:
        raise HTTPException(status_code=415, detail="Submit organisation details as JSON or a form with an optional document.")
    try:
        return schema.model_validate(values), document
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors(include_url=False))) from None


async def store_organization_document(organization_id: str, document: StarletteUploadFile) -> dict:
    filename = document.filename or ""
    if (
        not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or PurePosixPath(filename).name != filename
        or PureWindowsPath(filename).name != filename
        or any(ord(char) < 32 or ord(char) == 127 for char in filename)
    ):
        raise HTTPException(status_code=422, detail="Use a plain file name without folder paths.")
    original_filename = filename.strip()
    extension = PurePosixPath(original_filename).suffix.casefold()
    if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG, or JPG document.")
    contents = await document.read(MAX_ORGANIZATION_DOCUMENT_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=422, detail="The organisation document is empty.")
    if len(contents) > MAX_ORGANIZATION_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Organisation documents must be 5 MB or smaller.")
    file_type, content_type = identify_format(original_filename, contents)
    expected = {".pdf": "pdf", ".png": "image_png", ".jpg": "image_jpeg", ".jpeg": "image_jpeg"}[extension]
    if file_type != expected:
        raise HTTPException(status_code=415, detail="The file contents do not match the selected file type.")
    if file_type in {"image_png", "image_jpeg"}:
        normalized = sniff_and_normalize(contents)
        if normalized.content_type != content_type:
            raise HTTPException(status_code=415, detail="The file contents do not match the selected image type.")
        contents = normalized.normalized_bytes
    else:
        try:
            pdf = pymupdf.open(stream=contents, filetype="pdf")
            if pdf.is_encrypted:
                raise HTTPException(status_code=422, detail="Password-protected PDFs cannot be submitted.")
            pdf.close()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail="The PDF document is invalid or unreadable.") from exc
    if len(original_filename) > 240:
        original_filename = original_filename[:240]
    object_key = safe_filename(original_filename)
    storage = get_storage()
    storage.put(organization_id, object_key, BytesIO(contents), content_type)
    return {
        "document_ref": object_key,
        "original_filename": original_filename,
        "content_type": content_type,
        "sha256": sha256(contents).hexdigest(),
        "size_bytes": len(contents),
    }


def organization_response(org: Organization, db: Session, viewer: User | None = None) -> OrganizationResponse:
    submissions = db.execute(
        select(OrganizationSubmission, User.display_name)
        .join(User, User.id == OrganizationSubmission.submitted_by_user_id)
        .where(OrganizationSubmission.organization_id == org.id)
        .order_by(OrganizationSubmission.created_at.asc(), OrganizationSubmission.id.asc())
    ).all()
    request_row = db.execute(
        select(VerificationDecision, User.display_name)
        .join(User, User.id == VerificationDecision.actor_user_id)
        .where(
            VerificationDecision.organization_id == org.id,
            VerificationDecision.decision == "more_information_required",
        )
        .order_by(VerificationDecision.created_at.desc(), VerificationDecision.id.desc())
        .limit(1)
    ).first()
    latest_request = None
    if request_row:
        decision, actor_name = request_row
        latest_request = VerificationHistoryItem(
            id=decision.id,
            decision=decision.decision,
            note=decision.note,
            actor_name=actor_name,
            created_at=decision.created_at,
        )
    return OrganizationResponse.model_validate(org).model_copy(update={
        "can_resubmit": bool(viewer and org.created_by == viewer.id and org.verification_status == "more_information_required"),
        "latest_admin_request": latest_request,
        "submissions": [
            OrganizationSubmissionResponse(
                id=submission.id,
                note=submission.note,
                submitted_by_name=display_name,
                created_at=submission.created_at,
                original_filename=submission.original_filename,
                content_type=submission.content_type,
                size_bytes=submission.size_bytes,
            )
            for submission, display_name in submissions
        ],
    })


@router.get("/orgs", response_model=list[OrganizationSummary])
def list_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Organization, Membership.role).join(Membership, Membership.organization_id == Organization.id).where(Membership.user_id == user.id, Organization.deleted_at.is_(None)).order_by(Organization.created_at.desc())).all()
    return [OrganizationSummary(id=org.id, name=org.name, industry=org.industry, verification_status=org.verification_status, role=role) for org, role in rows]


@router.post("/orgs", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED, openapi_extra=organization_submission_openapi_extra("OrganizationCreate"))
async def create_organization(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload, document = await parse_organization_request(request, OrganizationCreate)
    host = client_ip(request)
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
    stored_document = await store_organization_document(org.id, document) if document else {}
    db.add(OrganizationSubmission(organization_id=org.id, submitted_by_user_id=user.id, **stored_document))
    db.add(AuditEvent(organization_id=org.id, actor_user_id=user.id, action="organization.submitted_for_verification", entity_type="organization", entity_id=org.id, details={"status": "pending_verification"}))
    try:
        db.commit()
    except Exception:
        db.rollback()
        if stored_document:
            get_storage().delete(org.id, stored_document["document_ref"])
        raise
    db.refresh(org)
    return organization_response(org, db, user)


@router.get("/orgs/{organization_id}", response_model=OrganizationResponse)
def get_organization(organization_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    get_member(organization_id, context.user.id, db)
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return organization_response(org, db, context.user)


@router.post("/orgs/{organization_id}/resubmit", response_model=OrganizationResponse, openapi_extra=organization_submission_openapi_extra("OrganizationResubmit"))
async def resubmit_organization(organization_id: str, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload, document = await parse_organization_request(request, OrganizationResubmit)
    enforce_rate_limit(f"resubmit-org:{organization_id}:{user.id}:{client_ip(request)}", limit=5, window_seconds=3600)
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)).with_for_update())
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    if org.created_by != user.id:
        raise HTTPException(status_code=403, detail="Only the organisation creator can resubmit it.")
    if org.verification_status != "more_information_required":
        raise HTTPException(status_code=409, detail="This organisation is not waiting for more information.")
    org.name = payload.name
    org.industry = payload.industry
    org.official_email = str(payload.official_email).strip().lower()
    org.website = str(payload.website)
    org.contact_person = payload.contact_person
    org.verification_status = "pending_verification"
    stored_document = await store_organization_document(org.id, document) if document else {}
    db.add(OrganizationSubmission(organization_id=org.id, submitted_by_user_id=user.id, note=payload.note.strip() if payload.note and payload.note.strip() else None, **stored_document))
    db.add(AuditEvent(organization_id=org.id, actor_user_id=user.id, action="organization.resubmitted_for_verification", entity_type="organization", entity_id=org.id, details={"status": "pending_verification", "note_present": bool(payload.note and payload.note.strip())}))
    try:
        db.commit()
    except Exception:
        db.rollback()
        if stored_document:
            get_storage().delete(org.id, stored_document["document_ref"])
        raise
    db.refresh(org)
    return organization_response(org, db, user)


@router.get("/orgs/{organization_id}/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(organization_id: str, action: str | None = None, offset: int = 0, limit: int = 50, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Use an offset of zero or more and a page size from 1 to 100.")
    statement = select(AuditEvent, User.display_name).outerjoin(User, User.id == AuditEvent.actor_user_id).where(AuditEvent.organization_id == organization_id)
    if action:
        statement = statement.where(AuditEvent.action.ilike(f"%{action[:80]}%"))
    rows = db.execute(statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id).offset(offset).limit(limit)).all()
    return [AuditEventResponse(id=event.id, actor_user_id=event.actor_user_id, actor_name=actor_name, action=event.action, entity_type=event.entity_type, entity_id=event.entity_id, details=_safe_audit_details(event.details or {}), created_at=event.created_at) for event, actor_name in rows]


@router.post("/orgs/{organization_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(payload: InviteCreate, organization_id: str, request: Request, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    enforce_rate_limit(f"invite-create:{organization_id}:{membership.user_id}:{client_ip(request)}", limit=10, window_seconds=3600)
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
def redeem_invite(payload: InviteRedeem, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    host = client_ip(request)
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
    record_notification(db, user_id=user.id, organization_id=org.id, kind="invite_received", payload={"organization_id": org.id, "organization_name": org.name, "role": invite.role})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already belong to this organisation.") from None
    send_user_email(db, sender, user_id=user.id, organization_id=org.id, subject=f"You joined {org.name} on BrandLens", text=f"You joined {org.name} as {invite.role}.")
    return {"message": "You joined the organisation.", "organization_id": org.id, "role": invite.role}


@router.get("/platform/verifications", response_model=list[OrganizationResponse])
def verification_queue(status_filter: str = Query(default="pending", alias="status", pattern="^(pending|awaiting_info)$"), _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    verification_status = "pending_verification" if status_filter == "pending" else "more_information_required"
    organizations = db.scalars(select(Organization).where(Organization.verification_status == verification_status, Organization.deleted_at.is_(None)).order_by(Organization.created_at.asc())).all()
    return [organization_response(org, db) for org in organizations]


@router.get("/platform/verifications/{organization_id}/history", response_model=list[VerificationHistoryItem])
def verification_history(organization_id: str, _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(VerificationDecision, User.display_name).join(User, User.id == VerificationDecision.actor_user_id).where(VerificationDecision.organization_id == organization_id).order_by(VerificationDecision.created_at.desc())).all()
    if not db.get(Organization, organization_id):
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return [VerificationHistoryItem(id=decision.id, decision=decision.decision, note=decision.note, actor_name=name, created_at=decision.created_at) for decision, name in rows]


@router.get("/platform/verifications/{organization_id}/submissions/{submission_id}/document")
def download_organization_submission_document(organization_id: str, submission_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)))
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    submission = db.scalar(select(OrganizationSubmission).where(OrganizationSubmission.organization_id == org.id, OrganizationSubmission.id == submission_id))
    if not submission or not submission.document_ref:
        raise HTTPException(status_code=404, detail="No document was submitted for this version.")
    is_platform_admin = db.get(PlatformAdmin, context.user.id) is not None
    if not is_platform_admin and org.created_by != context.user.id:
        raise HTTPException(status_code=403, detail="Only the organisation creator or a platform administrator can download this document.")
    storage = get_storage()
    local_path = storage.local_path(org.id, submission.document_ref)
    if local_path is not None and not local_path.is_file():
        raise HTTPException(status_code=404, detail="The stored document is unavailable.")
    try:
        chunks, _stored_type = storage.stream(org.id, submission.document_ref)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="The stored document is unavailable.") from exc
    filename = submission.original_filename or "organisation-document"
    headers = {
        "Cache-Control": "private, no-store",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(chunks, media_type=submission.content_type or "application/octet-stream", headers=headers)


@router.post("/platform/verifications/{organization_id}/decision", response_model=OrganizationResponse)
def decide_verification(organization_id: str, payload: VerificationDecisionRequest, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    org = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.deleted_at.is_(None)).with_for_update())
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    if org.verification_status != "pending_verification":
        raise HTTPException(status_code=409, detail="This organisation is not awaiting verification.")
    if org.created_by == admin.id:
        raise HTTPException(status_code=403, detail="A platform administrator cannot verify an organisation they submitted.")
    if payload.decision in {"rejected", "more_information_required"} and not (payload.note and payload.note.strip()):
        raise HTTPException(status_code=422, detail="Add a note explaining this decision.")
    org.verification_status = payload.decision
    db.add(VerificationDecision(organization_id=org.id, actor_user_id=admin.id, decision=payload.decision, note=payload.note.strip() if payload.note else None))
    db.add(AuditEvent(organization_id=org.id, actor_user_id=admin.id, action=f"organization.verification.{payload.decision}", entity_type="organization", entity_id=org.id, details={"status": payload.decision}))
    record_notification(db, user_id=org.created_by, organization_id=org.id, kind="organization_verification_result", payload={"organization_id": org.id, "organization_name": org.name, "decision": payload.decision, "note": payload.note})
    db.commit()
    db.refresh(org)
    send_user_email(db, sender, user_id=org.created_by, organization_id=org.id, subject=f"BrandLens organisation verification: {org.name}", text=f"Your organisation status is now {payload.decision.replace('_', ' ')}.\n{payload.note or ''}")
    return organization_response(org, db, admin)


