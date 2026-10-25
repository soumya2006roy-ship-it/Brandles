from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_auth_context, require_org_role
from app.core.db import get_db
from app.core.security import as_utc
from app.db.models import AuditEvent, BrandGuidelineSource, Membership, Organization, Rule, SourcePassage, User
from app.sources.documents import chunk_block, extract_document, identify_format, local_hash_embedding, read_upload
from app.sources.schemas import PassageDetailResponse, RuleDecision, RuleResponse, RuleWrite, SourceDetailResponse, SourceEffectiveDates, SourcePassageResponse, SourceResponse
from app.storage.factory import get_storage
from app.storage.local import safe_filename

router = APIRouter(tags=["approved-sources-and-rules"])


def _source_member(org_id: str, user: User, db: Session) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id))
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    org = db.scalar(select(Organization).where(Organization.id == org_id, Organization.deleted_at.is_(None)))
    if not org or org.verification_status != "approved":
        raise HTTPException(status_code=423, detail="This organisation is not approved for workspace actions.")
    return membership


def _ensure_source_passage(org_id: str, passage_id: str, db: Session, *, approved: bool = False) -> SourcePassage:
    passage = db.scalar(select(SourcePassage).where(SourcePassage.organization_id == org_id, SourcePassage.id == passage_id))
    if not passage:
        raise HTTPException(status_code=404, detail="Source passage not found.")
    if approved:
        source = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.id == passage.source_id))
        if not source or source.status != "approved":
            raise HTTPException(status_code=409, detail="Rules must reference a passage from an approved source version.")
    return passage


@router.get("/orgs/{org_id}/sources", response_model=list[SourceResponse])
def list_sources(org_id: str, status: str | None = None, query: str | None = Query(default=None, max_length=200), family_id: str | None = None, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _source_member(org_id, context.user, db)
    statement = select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id)
    if status:
        if status not in {"draft", "approved", "archived"}:
            raise HTTPException(status_code=422, detail="Unknown source status filter.")
        statement = statement.where(BrandGuidelineSource.status == status)
    if query and query.strip():
        needle = f"%{query.strip()}%"
        passage_ids = select(SourcePassage.source_id).where(SourcePassage.organization_id == org_id, SourcePassage.text.ilike(needle))
        statement = statement.where((BrandGuidelineSource.title.ilike(needle)) | (BrandGuidelineSource.original_filename.ilike(needle)) | BrandGuidelineSource.id.in_(passage_ids))
    if family_id:
        statement = statement.where(BrandGuidelineSource.family_id == family_id)
    return db.scalars(statement.order_by(BrandGuidelineSource.created_at.desc())).all()


@router.post("/orgs/{org_id}/sources", response_model=SourceResponse, status_code=201)
async def upload_source(
    org_id: str,
    title: str = Form(min_length=2, max_length=240),
    source_family_id: str | None = Form(default=None),
    document: UploadFile = File(),
    membership: Membership = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Add a title for this source.")
    original_filename = Path(document.filename or "source-document").name[:240]
    contents = await read_upload(document)
    file_type, content_type = identify_format(original_filename, contents)
    blocks = extract_document(file_type, contents)
    if source_family_id:
        previous = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.family_id == source_family_id).order_by(BrandGuidelineSource.version.desc()).with_for_update())
        if not previous:
            raise HTTPException(status_code=404, detail="Source version history not found.")
        family_id = previous.family_id
        version = previous.version + 1
        title = previous.title
    else:
        family_id = str(uuid4())
        version = 1
    object_key = safe_filename(original_filename)
    storage = get_storage()
    storage.put(org_id, object_key, BytesIO(contents), content_type)
    source = BrandGuidelineSource(
        organization_id=org_id,
        family_id=family_id,
        title=title,
        document_ref=object_key,
        original_filename=original_filename,
        content_type=content_type,
        sha256=sha256(contents).hexdigest(),
        size_bytes=len(contents),
        version=version,
        status="draft",
        created_by=membership.user_id,
    )
    db.add(source)
    db.flush()
    for block in blocks:
        for text, start, end in chunk_block(block):
            db.add(SourcePassage(
                organization_id=org_id,
                source_id=source.id,
                text=text,
                page_number=block.page_number,
                location_label=block.location_label,
                start_offset=start,
                end_offset=end,
                embedding=local_hash_embedding(text),
            ))
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="source.version_uploaded", entity_type="source", entity_id=source.id, details={"family_id": family_id, "version": version, "sha256": source.sha256, "chunks": sum(len(chunk_block(block)) for block in blocks)}))
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(org_id, object_key)
        raise
    db.refresh(source)
    return source


@router.get("/orgs/{org_id}/sources/{source_id}", response_model=SourceDetailResponse)
def get_source(org_id: str, source_id: str, query: str | None = Query(default=None, max_length=200), context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _source_member(org_id, context.user, db)
    source = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.id == source_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source version not found.")
    statement = select(SourcePassage).where(SourcePassage.organization_id == org_id, SourcePassage.source_id == source_id)
    if query and query.strip():
        statement = statement.where(SourcePassage.text.ilike(f"%{query.strip()}%"))
    passages = db.scalars(statement.order_by(SourcePassage.page_number, SourcePassage.start_offset)).all()
    return SourceDetailResponse.model_validate({**SourceResponse.model_validate(source, from_attributes=True).model_dump(), "passages": [SourcePassageResponse.model_validate(passage, from_attributes=True).model_dump() for passage in passages]})


@router.get("/orgs/{org_id}/passages/{passage_id}", response_model=PassageDetailResponse)
def get_passage(org_id: str, passage_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _source_member(org_id, context.user, db)
    row = db.execute(select(SourcePassage, BrandGuidelineSource).join(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id)).where(SourcePassage.organization_id == org_id, SourcePassage.id == passage_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Source passage not found.")
    passage, source = row
    return PassageDetailResponse.model_validate({**{field: getattr(passage, field) for field in ("id", "text", "page_number", "location_label", "start_offset", "end_offset")}, "source_id": source.id, "source_title": source.title, "source_version": source.version, "source_status": source.status})


@router.get("/orgs/{org_id}/sources/{source_id}/download")
def get_source_download(org_id: str, source_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _source_member(org_id, context.user, db)
    source = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.id == source_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source version not found.")
    url = get_storage().signed_download_url(org_id, source.document_ref, 300)
    if url.startswith("/api/v1/"):
        url = "/api/product/" + url.removeprefix("/api/v1/")
    return {"url": url}


@router.post("/orgs/{org_id}/sources/{source_id}/approve", response_model=SourceResponse)
def approve_source(org_id: str, source_id: str, dates: SourceEffectiveDates, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    source = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.id == source_id).with_for_update())
    if not source:
        raise HTTPException(status_code=404, detail="Source version not found.")
    if source.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft source versions can be approved.")
    if dates.effective_from and dates.effective_to and dates.effective_to < dates.effective_from:
        raise HTTPException(status_code=422, detail="Expiry date must be on or after the effective-from date.")
    old_approved = db.scalars(select(BrandGuidelineSource).where(BrandGuidelineSource.organization_id == org_id, BrandGuidelineSource.family_id == source.family_id, BrandGuidelineSource.status == "approved").with_for_update()).all()
    old_source_ids = [item.id for item in old_approved]
    for previous in old_approved:
        previous.status = "archived"
    if old_source_ids:
        old_passage_ids = select(SourcePassage.id).where(SourcePassage.organization_id == org_id, SourcePassage.source_id.in_(old_source_ids))
        old_rules = db.scalars(select(Rule).where(Rule.organization_id == org_id, Rule.source_passage_id.in_(old_passage_ids), Rule.status == "active")).all()
        for old_rule in old_rules:
            old_rule.status = "archived"
    source.effective_from = dates.effective_from
    source.effective_to = dates.effective_to
    source.status = "approved"
    source.approved_by = membership.user_id
    source.approved_at = datetime.now(UTC)
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="source.version_approved", entity_type="source", entity_id=source.id, details={"family_id": source.family_id, "version": source.version, "effective_from": dates.effective_from.isoformat() if dates.effective_from else None, "effective_to": dates.effective_to.isoformat() if dates.effective_to else None, "archived_versions": [item.id for item in old_approved]}))
    db.commit()
    db.refresh(source)
    return source


@router.get("/orgs/{org_id}/rules", response_model=list[RuleResponse])
def list_rules(org_id: str, status: str | None = None, rule_type: str | None = None, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _source_member(org_id, context.user, db)
    statement = select(Rule).where(Rule.organization_id == org_id)
    if status:
        if status not in {"suggested", "active", "archived", "rejected", "draft"}:
            raise HTTPException(status_code=422, detail="Unknown rule status filter.")
        statement = statement.where(Rule.status == status)
    if rule_type:
        statement = statement.where(Rule.rule_type == rule_type)
    return db.scalars(statement.order_by(Rule.created_at.desc())).all()


@router.post("/orgs/{org_id}/rules", response_model=RuleResponse, status_code=201)
def create_rule(org_id: str, payload: RuleWrite, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    membership = _source_member(org_id, context.user, db)
    if membership.role not in {"admin", "creator"}:
        raise HTTPException(status_code=403, detail="Only Admins can approve rules; Creators may submit suggestions.")
    if payload.valid_from and payload.valid_to and payload.valid_to < payload.valid_from:
        raise HTTPException(status_code=422, detail="Rule end date must be on or after its start date.")
    _ensure_source_passage(org_id, payload.source_passage_id, db, approved=True)
    status = "active" if membership.role == "admin" else "suggested"
    rule = Rule(organization_id=org_id, rule_type=payload.rule_type, parameters=payload.parameters, channel=payload.channel, valid_from=payload.valid_from, valid_to=payload.valid_to, source_passage_id=payload.source_passage_id, status=status, created_by=context.user.id)
    db.add(rule)
    db.flush()
    db.add(AuditEvent(organization_id=org_id, actor_user_id=context.user.id, action="rule.created" if status == "active" else "rule.suggested", entity_type="rule", entity_id=rule.id, details={"rule_type": rule.rule_type, "status": status, "source_passage_id": rule.source_passage_id}))
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/orgs/{org_id}/rules/{rule_id}/decision", response_model=RuleResponse)
def decide_rule(org_id: str, rule_id: str, decision: RuleDecision, membership: Membership = Depends(require_org_role("admin")), db: Session = Depends(get_db)):
    rule = db.scalar(select(Rule).where(Rule.organization_id == org_id, Rule.id == rule_id).with_for_update())
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")
    if rule.status != "suggested":
        raise HTTPException(status_code=409, detail="Only suggested rules can be reviewed.")
    if decision.decision == "approve":
        _ensure_source_passage(org_id, rule.source_passage_id or "", db, approved=True)
        rule.status = "active"
    else:
        rule.status = "rejected"
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action=f"rule.suggestion_{'approved' if decision.decision == 'approve' else 'rejected'}", entity_type="rule", entity_id=rule.id, details={"note": decision.note}))
    db.commit()
    db.refresh(rule)
    return rule
