from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.assets.media import MAX_ASSET_BYTES, difference_hash, get_ocr_provider, scan_for_malware, similarity, sniff_and_normalize
from app.auth.dependencies import get_auth_context, require_org_role
from app.campaigns.schemas import AssetResponse, CampaignCreate, CampaignDetailResponse, CampaignResponse, ClarificationRequest, FactResponse, FindingDecision, FindingResponse, ReviewDecision, ReviewResponse, ReviewSubmit, ScanResponse
from app.core.db import get_db
from app.core.config import get_settings
from app.core.mail import EmailSender, get_email_sender
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, ExtractedFact, Finding, Membership, Notification, Organization, Review, Rule, Scan, SourcePassage
from app.notifications.schemas import NotificationResponse
from app.notifications.service import record_notification, send_user_email
from app.sources.documents import clean_text, extract_document, identify_format
from app.storage.factory import get_storage
from app.storage.local import safe_filename
from app.jobs.queue import enqueue
from app.campaigns.scans import active_rules_version

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
    campaign = _campaign(org_id, campaign_id, db, lock=True)
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
    # Any change to the current asset set invalidates campaign evidence and prior approvals.
    campaign.status = "draft"
    stale_scans = db.scalars(select(Scan).where(Scan.organization_id == org_id, ((Scan.campaign_id == campaign_id) | (Scan.asset_id == (previous.id if previous else ""))), Scan.status != "stale")).all()
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


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/scans", response_model=ScanResponse, status_code=202)
def create_campaign_scan(org_id: str, campaign_id: str, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db)):
    campaign = _campaign(org_id, campaign_id, db, lock=True)
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:organization_id))"), {"organization_id": org_id})
    active_scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.status.in_(["queued", "running"])).order_by(Scan.created_at.desc()).with_for_update())
    if active_scan:
        if active_scan.campaign_id == campaign_id:
            return ScanResponse.model_validate({**active_scan.__dict__, "finding_count": db.scalar(select(func.count(Finding.id)).where(Finding.organization_id == org_id, Finding.scan_id == active_scan.id)) or 0})
        raise HTTPException(status_code=409, detail="Another campaign scan is already running for this organisation.")
    assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.current.is_(True), Asset.deleted_at.is_(None))).all()
    if not assets:
        raise HTTPException(status_code=422, detail="Add at least one current asset before scanning.")
    if len(assets) > get_settings().scan_max_assets:
        raise HTTPException(status_code=413, detail=f"A campaign scan can include at most {get_settings().scan_max_assets} current assets.")
    scan = Scan(organization_id=org_id, campaign_id=campaign_id, status="queued", requested_by=membership.user_id, rules_version="pending")
    db.add(scan)
    db.flush()
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="campaign.scan_queued", entity_type="scan", entity_id=scan.id, details={"campaign_id": campaign.id, "asset_count": len(assets)}))
    db.commit()
    try:
        enqueue("campaign_scan", {"organization_id": org_id, "scan_id": scan.id})
    except Exception as exc:
        scan.status = "failed"
        scan.completed_at = datetime.now(UTC)
        db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="campaign.scan_queue_failed", entity_type="scan", entity_id=scan.id, details={"reason": "Background queue unavailable."}))
        db.commit()
        raise HTTPException(status_code=503, detail="The scan queue is unavailable. Try again when the workspace worker is running.") from exc
    return ScanResponse.model_validate({**scan.__dict__, "finding_count": 0})


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/cancel", response_model=ScanResponse)
def cancel_campaign_scan(org_id: str, campaign_id: str, scan_id: str, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db)):
    _campaign(org_id, campaign_id, db, lock=True)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == scan_id).with_for_update())
    if not scan:
        raise HTTPException(status_code=404, detail="Campaign scan not found.")
    if scan.status == "queued":
        scan.status = "cancelled"
        scan.completed_at = datetime.now(UTC)
    elif scan.status == "running":
        scan.cancel_requested = True
    else:
        raise HTTPException(status_code=409, detail="Only queued or running scans can be cancelled.")
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="campaign.scan_cancel_requested", entity_type="scan", entity_id=scan.id))
    db.commit()
    return ScanResponse.model_validate({**scan.__dict__, "finding_count": 0})


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/resume", response_model=ScanResponse, status_code=202)
def resume_campaign_scan(org_id: str, campaign_id: str, scan_id: str, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db)):
    campaign = _campaign(org_id, campaign_id, db, lock=True)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == scan_id).with_for_update())
    if not scan:
        raise HTTPException(status_code=404, detail="Campaign scan not found.")
    if scan.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Only failed or cancelled scans can be resumed.")
    if scan.completed_asset_ids:
        current_assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.current.is_(True), Asset.deleted_at.is_(None))).all()
        as_of = (campaign.planned_publish_date.date() if campaign.planned_publish_date else None) or campaign.starts_at or campaign.ends_at or datetime.now(UTC).date()
        if scan.asset_versions != {asset.id: asset.version for asset in current_assets} or scan.rules_version != active_rules_version(db, org_id, as_of):
            raise HTTPException(status_code=409, detail="Campaign evidence changed after this scan. Start a fresh scan instead of resuming.")
    scan.status = "queued"
    scan.cancel_requested = False
    scan.completed_at = None
    scan.progress = 0
    scan.requested_by = membership.user_id
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="campaign.scan_resumed", entity_type="scan", entity_id=scan.id))
    db.commit()
    try:
        enqueue("campaign_scan", {"organization_id": org_id, "scan_id": scan.id})
    except Exception as exc:
        scan.status = "failed"
        scan.completed_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=503, detail="The scan queue is unavailable.") from exc
    return ScanResponse.model_validate({**scan.__dict__, "finding_count": 0})


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/scans", response_model=list[ScanResponse])
def list_campaign_scans(org_id: str, campaign_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    _campaign(org_id, campaign_id, db)
    scans = db.scalars(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id).order_by(Scan.created_at.desc())).all()
    return [ScanResponse.model_validate({**scan.__dict__, "finding_count": db.scalar(select(func.count(Finding.id)).where(Finding.organization_id == org_id, Finding.scan_id == scan.id)) or 0}) for scan in scans]


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}", response_model=ScanResponse)
def get_campaign_scan(org_id: str, campaign_id: str, scan_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    _campaign(org_id, campaign_id, db)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == scan_id))
    if not scan:
        raise HTTPException(status_code=404, detail="Campaign scan not found.")
    return ScanResponse.model_validate({**scan.__dict__, "finding_count": db.scalar(select(func.count(Finding.id)).where(Finding.organization_id == org_id, Finding.scan_id == scan.id)) or 0})


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/findings", response_model=list[FindingResponse])
def list_campaign_findings(org_id: str, campaign_id: str, scan_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    _campaign(org_id, campaign_id, db)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == scan_id))
    if not scan:
        raise HTTPException(status_code=404, detail="Campaign scan not found.")
    rows = db.execute(select(Finding, SourcePassage, BrandGuidelineSource).outerjoin(SourcePassage, (SourcePassage.organization_id == Finding.organization_id) & (SourcePassage.id == Finding.source_passage_id)).outerjoin(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id)).where(Finding.organization_id == org_id, Finding.scan_id == scan_id).order_by(Finding.created_at, Finding.id)).all()
    return [FindingResponse.model_validate({**finding.__dict__, "source_title": source.title if source else None, "source_version": source.version if source else None, "source_text": passage.text if passage else None}) for finding, passage, source in rows]


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/facts", response_model=list[FactResponse])
def list_campaign_facts(org_id: str, campaign_id: str, scan_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    _campaign(org_id, campaign_id, db)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == scan_id))
    if not scan:
        raise HTTPException(status_code=404, detail="Campaign scan not found.")
    rows = db.execute(select(ExtractedFact, Asset.channel).join(Asset, (Asset.organization_id == ExtractedFact.organization_id) & (Asset.id == ExtractedFact.asset_id)).where(ExtractedFact.organization_id == org_id, ExtractedFact.campaign_id == campaign_id, ExtractedFact.fact_type.in_(["percentage", "currency", "date", "claim"])).order_by(Asset.channel, ExtractedFact.fact_type, ExtractedFact.value)).all()
    return [FactResponse(id=fact.id, asset_id=fact.asset_id, channel=channel, fact_type=fact.fact_type, value=fact.value, asset_location=fact.asset_location, source_passage_id=fact.source_passage_id) for fact, channel in rows]


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/findings/{finding_id}/decision", response_model=FindingResponse)
def decide_finding(org_id: str, campaign_id: str, finding_id: str, payload: FindingDecision, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db)):
    _campaign(org_id, campaign_id, db)
    finding = db.scalar(select(Finding).join(Scan, (Scan.organization_id == Finding.organization_id) & (Scan.id == Finding.scan_id)).where(Finding.organization_id == org_id, Finding.id == finding_id, Scan.campaign_id == campaign_id))
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    if finding.status not in {"open", "clarification_requested"}:
        raise HTTPException(status_code=409, detail="This finding is no longer open.")
    if payload.decision == "dismiss" and not (payload.dismissal_reason or "").strip():
        raise HTTPException(status_code=422, detail="Add a reason before dismissing a finding.")
    if payload.decision == "resolve" and not (payload.resolution or "").strip():
        raise HTTPException(status_code=422, detail="Describe the edit or resolution before closing a finding.")
    finding.status = "dismissed" if payload.decision == "dismiss" else "resolved"
    finding.dismissal_reason = (payload.dismissal_reason or "").strip() or None
    finding.resolution = (payload.resolution or "").strip() or None
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action=f"finding.{payload.decision}d" if payload.decision == "resolve" else "finding.dismissed", entity_type="finding", entity_id=finding.id, details={"scan_id": finding.scan_id, "reason": finding.dismissal_reason or finding.resolution}))
    db.commit()
    db.refresh(finding)
    passage = db.get(SourcePassage, finding.source_passage_id) if finding.source_passage_id else None
    source = db.get(BrandGuidelineSource, passage.source_id) if passage else None
    return FindingResponse.model_validate({**finding.__dict__, "source_title": source.title if source else None, "source_version": source.version if source else None, "source_text": passage.text if passage else None})


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/findings/{finding_id}/clarification", response_model=FindingResponse)
def request_finding_clarification(org_id: str, campaign_id: str, finding_id: str, payload: ClarificationRequest, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    _campaign(org_id, campaign_id, db)
    finding = db.scalar(select(Finding).join(Scan, (Scan.organization_id == Finding.organization_id) & (Scan.id == Finding.scan_id)).where(Finding.organization_id == org_id, Finding.id == finding_id, Scan.campaign_id == campaign_id))
    if not finding or finding.status not in {"open", "clarification_requested"}:
        raise HTTPException(status_code=404, detail="Open finding not found.")
    finding.status = "clarification_requested"
    finding.resolution = payload.question.strip()
    admins = db.scalars(select(Membership.user_id).where(Membership.organization_id == org_id, Membership.role == "admin")).all()
    for admin_id in admins:
        record_notification(db, user_id=admin_id, organization_id=org_id, kind="finding_clarification_requested", payload={"campaign_id": campaign_id, "finding_id": finding_id, "question": payload.question})
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="finding.clarification_requested", entity_type="finding", entity_id=finding.id, details={"scan_id": finding.scan_id, "question": payload.question}))
    db.commit()
    db.refresh(finding)
    for admin_id in admins:
        send_user_email(db, sender, user_id=admin_id, subject="BrandLens finding needs clarification", text=f"A campaign finding needs clarification.\nQuestion: {payload.question}")
    passage = db.get(SourcePassage, finding.source_passage_id) if finding.source_passage_id else None
    source = db.get(BrandGuidelineSource, passage.source_id) if passage else None
    return FindingResponse.model_validate({**finding.__dict__, "source_title": source.title if source else None, "source_version": source.version if source else None, "source_text": passage.text if passage else None})


def _review_response(row: Review, campaign: Campaign, asset: Asset) -> ReviewResponse:
    return ReviewResponse(id=row.id, submission_id=row.submission_id or row.id, campaign_id=campaign.id, campaign_name=campaign.name, asset_id=asset.id, asset_version=row.asset_version or asset.version, decision=row.decision, submitted_by_user_id=row.submitted_by_user_id, reviewer_user_id=row.reviewer_user_id, comment=row.comment, created_at=row.created_at)


def _scan_is_current(db: Session, organization_id: str, campaign_id: str, scan: Scan, assets: list[Asset]) -> bool:
    latest = db.scalar(select(Scan).where(Scan.organization_id == organization_id, Scan.campaign_id == campaign_id).order_by(Scan.created_at.desc(), Scan.id.desc()).limit(1))
    campaign = db.scalar(select(Campaign).where(Campaign.organization_id == organization_id, Campaign.id == campaign_id))
    as_of = (campaign.planned_publish_date.date() if campaign and campaign.planned_publish_date else None) or (campaign.starts_at if campaign else None) or (campaign.ends_at if campaign else None) or datetime.now(UTC).date()
    versions = {asset.id: asset.version for asset in assets}
    return bool(latest and latest.id == scan.id and scan.status == "completed" and scan.asset_versions == versions and scan.rules_version == active_rules_version(db, organization_id, as_of))


@router.post("/orgs/{org_id}/campaigns/{campaign_id}/submit", response_model=list[ReviewResponse], status_code=202)
def submit_campaign_for_review(org_id: str, campaign_id: str, payload: ReviewSubmit, membership: Membership = Depends(require_org_role("admin", "creator")), db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    campaign = _campaign(org_id, campaign_id, db, lock=True)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.campaign_id == campaign_id, Scan.id == payload.scan_id).with_for_update())
    assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.current.is_(True), Asset.deleted_at.is_(None)).order_by(Asset.id)).all()
    if not scan or not assets or not _scan_is_current(db, org_id, campaign_id, scan, assets):
        raise HTTPException(status_code=409, detail="Run a current completed scan before submitting this campaign.")
    if db.scalar(select(Finding.id).where(Finding.organization_id == org_id, Finding.scan_id == scan.id, Finding.status.in_(["open", "clarification_requested"]), Finding.severity.in_(["high", "critical"]))):
        raise HTTPException(status_code=409, detail="Resolve or dismiss High and Critical findings before submission.")
    pending = db.scalars(select(Review).where(Review.organization_id == org_id, Review.scan_id == scan.id, Review.decision == "pending").order_by(Review.created_at)).all()
    if pending:
        return [_review_response(row, campaign, asset) for row in pending if (asset := db.get(Asset, row.asset_id))]
    previous = db.scalars(select(Review).where(Review.organization_id == org_id, Review.scan_id == scan.id, Review.decision == "approved").order_by(Review.created_at)).all()
    if previous and {row.asset_id: row.asset_version for row in previous} == {asset.id: asset.version for asset in assets}:
        return [_review_response(row, campaign, asset) for row in previous if (asset := db.get(Asset, row.asset_id))]

    submission_id = str(uuid4())
    now = datetime.now(UTC)
    reviews = [Review(organization_id=org_id, asset_id=asset.id, asset_version=asset.version, submission_id=submission_id, submitted_by_user_id=membership.user_id, scan_id=scan.id, decision="pending", comment=payload.comment, created_at=now) for asset in assets]
    db.add_all(reviews)
    campaign.status = "in_review"
    reviewers = db.scalars(select(Membership.user_id).where(Membership.organization_id == org_id, Membership.role == "reviewer")).all()
    for reviewer_id in reviewers:
        record_notification(db, user_id=reviewer_id, organization_id=org_id, kind="review_submitted", payload={"campaign_id": campaign_id, "campaign_name": campaign.name, "submission_id": submission_id})
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action="campaign.submitted_for_review", entity_type="campaign", entity_id=campaign.id, details={"scan_id": scan.id, "submission_id": submission_id, "asset_versions": {asset.id: asset.version for asset in assets}}))
    db.commit()
    for reviewer_id in reviewers:
        send_user_email(db, sender, user_id=reviewer_id, subject=f"BrandLens review requested: {campaign.name}", text=f"A campaign was submitted for review. Open the organisation workspace to inspect findings and asset versions.\nCampaign: {campaign.name}")
    return [_review_response(row, campaign, asset) for row, asset in zip(reviews, assets, strict=False)]


@router.get("/orgs/{org_id}/reviews/queue", response_model=list[ReviewResponse])
def review_queue(org_id: str, _membership: Membership = Depends(require_org_role("reviewer")), db: Session = Depends(get_db)):
    rows = db.execute(select(Review, Campaign, Asset).join(Asset, (Asset.organization_id == Review.organization_id) & (Asset.id == Review.asset_id)).join(Campaign, (Campaign.organization_id == Asset.organization_id) & (Campaign.id == Asset.campaign_id)).where(Review.organization_id == org_id, Review.decision == "pending", Asset.current.is_(True), Asset.version == Review.asset_version).order_by(Review.created_at.desc())).all()
    final_submissions = set(db.scalars(select(Review.submission_id).where(Review.organization_id == org_id, Review.decision.in_(["approved", "rejected", "request_changes"]), Review.submission_id.is_not(None))).all())
    queue = []
    for row, campaign, asset in rows:
        if row.submission_id in final_submissions:
            continue
        scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.id == row.scan_id, Scan.campaign_id == campaign.id))
        current_assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign.id, Asset.current.is_(True), Asset.deleted_at.is_(None))).all()
        if scan and _scan_is_current(db, org_id, campaign.id, scan, current_assets):
            queue.append(_review_response(row, campaign, asset))
    return queue


@router.get("/orgs/{org_id}/campaigns/{campaign_id}/reviews", response_model=list[ReviewResponse])
def campaign_review_history(org_id: str, campaign_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    campaign = _campaign(org_id, campaign_id, db)
    rows = db.execute(select(Review, Asset).join(Asset, (Asset.organization_id == Review.organization_id) & (Asset.id == Review.asset_id)).where(Review.organization_id == org_id, Asset.campaign_id == campaign_id).order_by(Review.created_at)).all()
    return [_review_response(row, campaign, asset) for row, asset in rows]


@router.post("/orgs/{org_id}/reviews/{submission_id}/decision", response_model=list[ReviewResponse])
def decide_review_submission(org_id: str, submission_id: str, payload: ReviewDecision, membership: Membership = Depends(require_org_role("reviewer")), db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    if payload.decision in {"reject", "request_changes"} and not (payload.comment or "").strip():
        raise HTTPException(status_code=422, detail="Add a comment when rejecting or requesting changes.")
    prior = db.scalars(select(Review).where(Review.organization_id == org_id, Review.submission_id == submission_id, Review.reviewer_user_id == membership.user_id, Review.decision != "pending").order_by(Review.created_at)).all()
    if prior:
        if all(row.decision == {"approve": "approved", "reject": "rejected", "request_changes": "changes_requested"}[payload.decision] for row in prior):
            asset = db.get(Asset, prior[0].asset_id)
            campaign = db.get(Campaign, asset.campaign_id) if asset else None
            if campaign and asset:
                return [_review_response(row, campaign, db.get(Asset, row.asset_id)) for row in prior if db.get(Asset, row.asset_id)]
        raise HTTPException(status_code=409, detail="This review submission already has a different decision.")
    pending = db.scalars(select(Review).where(Review.organization_id == org_id, Review.submission_id == submission_id, Review.decision == "pending").with_for_update()).all()
    if not pending:
        raise HTTPException(status_code=404, detail="Pending review submission not found.")
    assets = [db.get(Asset, row.asset_id) for row in pending]
    if any(asset is None for asset in assets):
        raise HTTPException(status_code=409, detail="A submitted asset version is no longer available.")
    campaign_ids = {asset.campaign_id for asset in assets if asset}
    if len(campaign_ids) != 1:
        raise HTTPException(status_code=409, detail="Review submission contains assets from multiple campaigns.")
    campaign_id = next(iter(campaign_ids))
    campaign = _campaign(org_id, campaign_id, db, lock=True)
    scan = db.scalar(select(Scan).where(Scan.organization_id == org_id, Scan.id == pending[0].scan_id, Scan.campaign_id == campaign_id))
    current_assets = db.scalars(select(Asset).where(Asset.organization_id == org_id, Asset.campaign_id == campaign_id, Asset.current.is_(True), Asset.deleted_at.is_(None)).order_by(Asset.id)).all()
    expected_versions = {row.asset_id: row.asset_version for row in pending}
    if not scan or not _scan_is_current(db, org_id, campaign_id, scan, current_assets) or expected_versions != {asset.id: asset.version for asset in current_assets}:
        raise HTTPException(status_code=409, detail="Campaign assets or approved rules changed after submission. Submit a fresh scan.")
    if any(row.submitted_by_user_id == membership.user_id for row in pending) or any(asset.created_by == membership.user_id for asset in current_assets):
        raise HTTPException(status_code=403, detail="A reviewer cannot approve their own submission.")
    if payload.decision == "approve" and db.scalar(select(Finding.id).where(Finding.organization_id == org_id, Finding.scan_id == scan.id, Finding.status.in_(["open", "clarification_requested"]), Finding.severity.in_(["high", "critical"]))):
        raise HTTPException(status_code=409, detail="Resolve or dismiss High and Critical findings before approval.")
    decision = {"approve": "approved", "reject": "rejected", "request_changes": "changes_requested"}[payload.decision]
    now = datetime.now(UTC)
    reviews = [Review(organization_id=org_id, asset_id=asset.id, asset_version=asset.version, submission_id=submission_id, submitted_by_user_id=row.submitted_by_user_id, scan_id=scan.id, reviewer_user_id=membership.user_id, decision=decision, comment=(payload.comment or "").strip() or None, created_at=now) for row, asset in zip(pending, current_assets, strict=False)]
    db.add_all(reviews)
    campaign.status = "approved" if decision == "approved" else decision
    recipients = {row.submitted_by_user_id for row in pending if row.submitted_by_user_id}
    recipients.update(asset.created_by for asset in current_assets if asset.created_by != membership.user_id)
    for recipient in recipients:
        record_notification(db, user_id=recipient, organization_id=org_id, kind=f"review_{decision}", payload={"campaign_id": campaign.id, "campaign_name": campaign.name, "submission_id": submission_id, "comment": payload.comment})
    db.add(AuditEvent(organization_id=org_id, actor_user_id=membership.user_id, action=f"campaign.review_{decision}", entity_type="campaign", entity_id=campaign.id, details={"scan_id": scan.id, "submission_id": submission_id, "asset_versions": {asset.id: asset.version for asset in current_assets}, "comment": payload.comment}))
    db.commit()
    for recipient in recipients:
        send_user_email(db, sender, user_id=recipient, subject=f"BrandLens review {decision.replace('_', ' ')}: {campaign.name}", text=f"A reviewer recorded {decision.replace('_', ' ')} for campaign {campaign.name}.\n{payload.comment or ''}")
    return [_review_response(row, campaign, asset) for row, asset in zip(reviews, current_assets, strict=False)]


@router.get("/orgs/{org_id}/notifications", response_model=list[NotificationResponse])
def list_notifications(org_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    return db.scalars(select(Notification).where(Notification.organization_id == org_id, Notification.user_id == context.user.id).order_by(Notification.created_at.desc()).limit(100)).all()


@router.post("/orgs/{org_id}/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(org_id: str, notification_id: str, context=Depends(get_auth_context), db: Session = Depends(get_db)):
    _campaign_member(org_id, context.user.id, db)
    notification = db.scalar(select(Notification).where(Notification.organization_id == org_id, Notification.user_id == context.user.id, Notification.id == notification_id))
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.read_at = notification.read_at or datetime.now(UTC)
    db.commit()
    return notification
