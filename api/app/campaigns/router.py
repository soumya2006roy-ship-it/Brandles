from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assets.media import MAX_ASSET_BYTES, difference_hash, get_ocr_provider, scan_for_malware, similarity, sniff_and_normalize
from app.auth.dependencies import get_auth_context, require_org_role
from app.campaigns.schemas import AssetResponse, CampaignCreate, CampaignDetailResponse, CampaignResponse
from app.core.db import get_db
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, ExtractedFact, Finding, Membership, Organization, Rule, Scan, SourcePassage
from app.sources.documents import clean_text, extract_document, identify_format
from app.storage.factory import get_storage
from app.storage.local import safe_filename

router = APIRouter(tags=["campaigns-and-assets"])
MAX_PASTED_TEXT_CHARACTERS = 200_000


def _campaign_member(org_id: str, user_id: str, db: Session) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user_id))
    organization = db.scalar(select(Organization).where(Organization.id == org_id, Organization.deleted_at.is_(None)))
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    if not organization or organization.verification_status != "approved":
        raise HTTPException(status_code=423, detail="This organisation is not approved for workspace actions.")
    return membership


def _campaign(org_id: str, campaign_id: str, db: Session, *, lock: bool = False) -> Campaign:
    statement = select(Campaign).where(Campaign.organization_id == org_id, Campaign.id == campaign_id, Campaign.deleted_at.is_(None))
    if lock:
        statement = statement.with_for_update()
    campaign = db.scalar(statement)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


def _source_is_effective(source: BrandGuidelineSource, today: date) -> bool:
    return source.status == "approved" and (source.effective_from is None or source.effective_from <= today) and (source.effective_to is None or source.effective_to >= today)


def _asset_logo_matches(org_id: str, asset_bytes: bytes, db: Session) -> list[dict]:
    rows = db.execute(
        select(Rule, SourcePassage, BrandGuidelineSource)
        .join(SourcePassage, (SourcePassage.organization_id == Rule.organization_id) & (SourcePassage.id == Rule.source_passage_id))
        .join(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id))
        .where(Rule.organization_id == org_id, Rule.status == "active", Rule.rule_type == "approved_logo", BrandGuidelineSource.content_type.like("image/%"))
    ).all()
    if not rows:
        return []
    uploaded_hash = difference_hash(asset_bytes)
    storage = get_storage()
    today = datetime.now(UTC).date()
    unique_sources: dict[str, tuple[Rule, BrandGuidelineSource]] = {}
    for rule, _passage, source in rows:
        if _source_is_effective(source, today) and (rule.valid_from is None or rule.valid_from <= today) and (rule.valid_to is None or rule.valid_to >= today):
            unique_sources.setdefault(source.id, (rule, source))
    matches: list[dict] = []
    for rule, source in unique_sources.values():
        try:
            local = storage.local_path(org_id, source.document_ref)
            if local is not None:
                logo_bytes = local.read_bytes()
            else:
                stream, _content_type = storage.stream(org_id, source.document_ref)
                logo_bytes = b"".join(stream)
            score = similarity(uploaded_hash, difference_hash(logo_bytes))
        except (OSError, ValueError):
            continue
        matches.append({"source_id": source.id, "source_title": source.title, "source_version": source.version, "logo_version": rule.parameters.get("version", str(source.version)), "similarity": round(score, 4), "matched": score >= 0.9, "method": "difference-hash-prototype"})
    return sorted(matches, key=lambda item: item["similarity"], reverse=True)[:5]


def _extract_asset_text(sniffed, contents: bytes) -> tuple[str | None, str]:
    if sniffed.asset_type == "image":
        ocr = get_ocr_provider()
        if ocr is None:
            return None, "not_configured"
        try:
            return ocr.extract(sniffed.normalized_bytes), "complete"
        except Exception:
            return None, "failed"
    if sniffed.text is not None:
        return sniffed.text, "complete"
    suffix = {"application/pdf": "pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}.get(sniffed.content_type)
    if not suffix:
        return None, "unavailable"
    try:
        file_type, _ = identify_format(f"asset.{suffix}", contents)
        blocks = extract_document(file_type, contents)
        return "\n\n".join(f"[{block.location_label or 'Document text'}]\n{block.text}" for block in blocks), "complete"
    except HTTPException as exc:
        if exc.detail == "No readable text was found in this document.":
            return None, "unavailable"
        raise


@router.get("/orgs/{org_id}/campaigns", response_model=list[CampaignResponse])
def list_campaigns(org_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    return db.scalars(select(Campaign).where(Campaign.organization_id == org_id, Campaign.deleted_at.is_(None)).order_by(Campaign.created_at.desc())).all()


@router.post("/orgs/{org_id}/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(org_id: str, payload: CampaignCreate, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    membership = _campaign_member(org_id, context.user.id, db)
    if membership.role not in {"admin", "creator"}:
        raise HTTPException(status_code=403, detail="Only Admins and Creators can create campaigns.")
    campaign = Campaign(organization_id=org_id, name=payload.name, channels=payload.channels, starts_at=payload.starts_at, ends_at=payload.ends_at, language=payload.language, status="draft", created_by=context.user.id)
    db.add(campaign)
    db.flush()
    db.add(AuditEvent(organization_id=org_id, actor_user_id=context.user.id, action="campaign.created", entity_type="campaign", entity_id=campaign.id, details={"channels": campaign.channels, "starts_at": payload.starts_at.isoformat() if payload.starts_at else None, "ends_at": payload.ends_at.isoformat() if payload.ends_at else None}))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/orgs/{org_id}/campaigns/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign(org_id: str, campaign_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    campaign = _campaign(org_id, campaign_id, db)
    assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id).order_by(Asset.asset_group_id, Asset.version.desc())).all()
    return CampaignDetailResponse.model_validate({**CampaignResponse.model_validate(campaign, from_attributes=True).model_dump(), "assets": [AssetResponse.model_validate(asset, from_attributes=True).model_dump() for asset in assets]})


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/assets", response_model=AssetResponse, status_code=201)
async def create_asset_version(
    org_id: str,
    campaign_id: str,
    channel: str = Form(min_length=2, max_length=50),
    language: str | None = Form(default=None, max_length=32),
    text_content: str | None = Form(default=None, max_length=MAX_PASTED_TEXT_CHARACTERS),
    asset_group_id: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    membership: Membership = Depends(require_org_role("admin", "creator")),
    db: Session = Depends(get_db),
):
    campaign = _campaign(org_id, campaign_id, db, lock=True)
    if channel not in campaign.channels:
        raise HTTPException(status_code=422, detail="Choose a channel that belongs to this campaign.")
    selected_language = (language or campaign.language).strip()
    if not selected_language:
        raise HTTPException(status_code=422, detail="Add a language code for this asset.")

    raw_bytes: bytes | None = None
    file_type: str | None = None
    content_type = "text/plain"
    original_filename: str | None = None
    malware_status = "not_configured"
    metadata_stripped = False
    extracted_text: str | None = None
    extraction_status = "complete"
    stored_bytes: bytes | None = None
    if file is not None:
        raw_bytes = await file.read(MAX_ASSET_BYTES + 1)
        if len(raw_bytes) > MAX_ASSET_BYTES:
            raise HTTPException(status_code=413, detail="Campaign assets must be 25 MB or smaller.")
        if not raw_bytes:
            raise HTTPException(status_code=422, detail="The uploaded asset is empty.")
        malware_status = scan_for_malware(raw_bytes)
        sniffed = sniff_and_normalize(raw_bytes)
        file_type = sniffed.asset_type
        content_type = sniffed.content_type
        stored_bytes = sniffed.normalized_bytes
        original_filename = (file.filename or "campaign-asset").replace("\\", "/").split("/")[-1][:240]
        extracted_text, extraction_status = _extract_asset_text(sniffed, raw_bytes)
        metadata_stripped = sniffed.metadata_stripped
        digest_bytes = stored_bytes
    else:
        if text_content is None or not text_content.strip():
            raise HTTPException(status_code=422, detail="Paste text or upload a file to create this asset.")
        if len(text_content) > MAX_PASTED_TEXT_CHARACTERS:
            raise HTTPException(status_code=413, detail="Pasted assets must be 200,000 characters or smaller.")
        text_content = clean_text(text_content).strip()
        if not text_content:
            raise HTTPException(status_code=422, detail="The pasted asset contains no readable text.")
        extracted_text = text_content
        digest_bytes = text_content.encode("utf-8")
        file_type = "text"
        malware_status = "not_applicable"
    if not digest_bytes:
        raise HTTPException(status_code=422, detail="The asset contains no readable content.")

    previous: Asset | None = None
    if asset_group_id:
        previous = db.scalar(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.asset_group_id == asset_group_id, Asset.current.is_(True)).with_for_update())
        if not previous:
            raise HTTPException(status_code=404, detail="Current asset version not found.")
        next_version = previous.version + 1
        group_id = previous.asset_group_id
    else:
        next_version = 1
        group_id = str(uuid4())

    storage = get_storage()
    object_key = safe_filename(original_filename or "asset") if stored_bytes is not None else None
    if object_key and stored_bytes is not None:
        storage.put(org_id, object_key, BytesIO(stored_bytes), content_type)
    if previous:
        previous.current = False
        stale_scans = db.scalars(select(Scan).where(Scan.organization_id == org_id, ((Scan.asset_id == previous.id) | ((Scan.asset_id.is_(None)) & (Scan.campaign_id == campaign_id))))).all()
        for scan in stale_scans:
            scan.status = "stale"
            for finding in db.scalars(select(Finding).where(Finding.organization_id == org_id, Finding.scan_id == scan.id)):
                finding.status = "stale"

    logo_matches = _asset_logo_matches(org_id, stored_bytes, db) if file_type == "image" and stored_bytes is not None else []
    asset = Asset(
        organization_id=org_id,
        campaign_id=campaign_id,
        asset_type=file_type,
        channel=channel.strip(),
        language=selected_language,
        asset_group_id=group_id,
        version=next_version,
        current=True,
        supersedes_asset_id=previous.id if previous else None,
        file_ref=object_key,
        original_filename=original_filename,
        content_type=content_type,
        sha256=sha256(digest_bytes).hexdigest(),
        size_bytes=len(digest_bytes),
        malware_status=malware_status,
        extraction_status=extraction_status,
        metadata_stripped=metadata_stripped,
        text_content=text_content,
        extracted_text=extracted_text,
        logo_matches=logo_matches,
        created_by=membership.user_id,
    )
    try:
        db.add(asset)
        db.flush()
        for match in logo_matches:
            db.add(ExtractedFact(organization_id=org_id, campaign_id=campaign_id, asset_id=asset.id, fact_type="logo_version_match", value=match["logo_version"], source_passage_id=None, asset_location={"source_id": match["source_id"], "similarity": match["similarity"], "matched": match["matched"], "method": match["method"]}))
        db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="asset.version_uploaded" if previous else "asset.created", entity_type="asset", entity_id=asset.id, details={"campaign_id": campaign_id, "asset_group_id": group_id, "version": next_version, "channel": channel, "asset_type": file_type, "sha256": asset.sha256, "malware_status": malware_status, "extraction_status": extraction_status, "stale_asset_id": previous.id if previous else None}))
        db.commit()
    except Exception:
        db.rollback()
        if object_key:
            storage.delete(org_id, object_key)
        raise
    db.refresh(asset)
    return asset


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/assets/{asset_id}/download")
def get_asset_download(org_id: str, campaign_id: str, asset_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    asset = db.scalar(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.id == asset_id))
    if not asset or not asset.file_ref:
        raise HTTPException(status_code=404, detail="Campaign file not found.")
    url = get_storage().signed_download_url(org_id, asset.file_ref, 300)
    if url.startswith("/api/v1/"):
        url = "/api/product/" + url.removeprefix("/api/v1/")
    return {"url": url}
