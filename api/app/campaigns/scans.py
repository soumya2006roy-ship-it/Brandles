"""Evidence-first deterministic campaign scans and worker entry point."""

import re
import json
import time
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.ai.clients import LLMDisabledError, get_llm_client
from app.checks.judgement import JUDGEMENT_PROMPT_VERSION, JUDGEMENT_TASK_INSTRUCTIONS, parse_judgement, retrieve_top_passages
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, ExtractedFact, Finding, Organization, Rule, Scan, SourcePassage
from app.core.config import get_settings

PERCENT_RE = re.compile(r"(?<!\w)(\d{1,3}(?:\.\d+)?)\s*%")
CLAIM_CUES = re.compile(r"\b(?:claim|cure[sd]?|treat[sd]?|prevent[sd]?|clinically proven|proven|guarantee[sd]?|eliminate[sd]?|reduce[sd]?|improve[sd]?|safe|effective|dermatologist[- ]tested)\b|दावा|ठीक|इलाज|गारंटी|प्रमाणित|सुरक्षित|प्रभावी", re.IGNORECASE)
CURRENCY_RE = re.compile(r"(?<!\w)(?:[$€£₹]\s?\d[\d,]*(?:\.\d{1,2})?|(?:USD|INR|EUR|GBP)\s?\d[\d,]*(?:\.\d{1,2})?)(?!\w)", re.IGNORECASE)
DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")


def _normalize_currency(value: str) -> str:
    match = re.search(r"[$€£₹]|\b(?:USD|INR|EUR|GBP)\b", value, re.IGNORECASE)
    number = re.search(r"\d[\d,]*(?:\.\d{1,2})?", value)
    if not match or not number:
        return " ".join(value.split())
    code = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(match.group().upper(), match.group().upper())
    try:
        amount = Decimal(number.group().replace(",", ""))
        return f"{code} {amount.normalize():f}"
    except InvalidOperation:
        return f"{code} {number.group()}"


def _normalize_date(value: str) -> str:
    normalized = value.replace("/", "-")
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%d-%m-%y", "%m-%d-%y")
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).date().isoformat()
        except ValueError:
            continue
    return f"ambiguous:{normalized}"


def _eligible_rule_rows(db: Session, organization_id: str, scan_date: date):
    return db.execute(
        select(Rule, SourcePassage, BrandGuidelineSource)
        .join(SourcePassage, (SourcePassage.organization_id == Rule.organization_id) & (SourcePassage.id == Rule.source_passage_id))
        .join(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id))
        .where(
            Rule.organization_id == organization_id,
            Rule.status == "active",
            BrandGuidelineSource.status == "approved",
            BrandGuidelineSource.deleted_at.is_(None),
            (BrandGuidelineSource.effective_from.is_(None) | (BrandGuidelineSource.effective_from <= scan_date)),
            (BrandGuidelineSource.effective_to.is_(None) | (BrandGuidelineSource.effective_to >= scan_date)),
            (Rule.valid_from.is_(None) | (Rule.valid_from <= scan_date)),
            (Rule.valid_to.is_(None) | (Rule.valid_to >= scan_date)),
        )
        .order_by(Rule.id)
    ).all()


def _active_offer_rows(db: Session, organization_id: str):
    """Approved offer evidence regardless of its dates, so expiry can be reported."""
    return db.execute(
        select(Rule, SourcePassage, BrandGuidelineSource)
        .join(SourcePassage, (SourcePassage.organization_id == Rule.organization_id) & (SourcePassage.id == Rule.source_passage_id))
        .join(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id))
        .where(Rule.organization_id == organization_id, Rule.status == "active", Rule.rule_type.in_(["discount_percent", "offer_name"]), BrandGuidelineSource.status == "approved", BrandGuidelineSource.deleted_at.is_(None))
        .order_by(Rule.id)
    ).all()


def active_rules_version(db: Session, organization_id: str, scan_date: date) -> str:
    rows = _eligible_rule_rows(db, organization_id, scan_date)
    canonical = [{"id": rule.id, "type": rule.rule_type, "parameters": rule.parameters, "channel": rule.channel, "valid_from": rule.valid_from.isoformat() if rule.valid_from else None, "valid_to": rule.valid_to.isoformat() if rule.valid_to else None, "source_id": source.id, "source_version": source.version, "passage_id": passage.id} for rule, passage, source in rows]
    digest = sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
    return f"rules-v1-{digest}"


def _excerpt(text: str, start: int, end: int, context: int = 70) -> str:
    return text[max(0, start - context):min(len(text), end + context)].strip()


def _finding(
    *, scan: Scan, asset: Asset | None, rule: Rule | None, passage: SourcePassage | None,
    finding_type: str, severity: str, text: str | None, start: int | None,
    end: int | None, quoted_excerpt: str | None, confidence: float,
    suggested_fix: str, flagged_region: dict[str, Any] | None = None,
) -> Finding:
    region = dict(flagged_region or {})
    if text is not None and start is not None and end is not None:
        region.update({"start": start, "end": end, "text": text[start:end]})
    return Finding(
        organization_id=scan.organization_id, scan_id=scan.id,
        asset_id=asset.id if asset else None, finding_type=finding_type,
        severity=severity, status="open", flagged_region=region or None,
        rule_id=rule.id if rule else None, source_passage_id=passage.id if passage else None,
        quoted_excerpt=quoted_excerpt, confidence=confidence, suggested_fix=suggested_fix,
    )


def execute_campaign_scan(organization_id: str, scan_id: str) -> None:
    """Run a queued campaign scan. Findings are deterministic checks only."""
    with SessionLocal() as db:
        scan = db.scalar(select(Scan).where(Scan.organization_id == organization_id, Scan.id == scan_id))
        if not scan or scan.status != "queued" or not scan.campaign_id:
            return
        scan.status = "running"
        db.commit()
        try:
            campaign = db.scalar(select(Campaign).where(Campaign.organization_id == organization_id, Campaign.id == scan.campaign_id, Campaign.deleted_at.is_(None)))
            if not campaign:
                raise ValueError("Campaign is unavailable.")
            assets = db.scalars(select(Asset).where(Asset.organization_id == organization_id, Asset.campaign_id == campaign.id, Asset.current.is_(True), Asset.deleted_at.is_(None)).order_by(Asset.id)).all()
            if not assets:
                raise ValueError("Add at least one current asset before scanning.")
            today = datetime.now(UTC).date()
            reference_date = campaign.planned_publish_date.date() if campaign.planned_publish_date else campaign.starts_at or campaign.ends_at or today
            rows = _eligible_rule_rows(db, organization_id, reference_date)
            offer_rows = _active_offer_rows(db, organization_id)
            expected_asset_versions = {asset.id: asset.version for asset in assets}
            expected_rules_version = active_rules_version(db, organization_id, reference_date)
            if scan.completed_asset_ids and (scan.asset_versions != expected_asset_versions or scan.rules_version != expected_rules_version):
                raise ValueError("Campaign evidence changed during the interrupted scan; start a fresh scan.")
            if not scan.completed_asset_ids:
                for old in db.scalars(select(Finding).where(Finding.organization_id == organization_id, Finding.scan_id == scan.id)).all():
                    db.delete(old)
                for old_fact in db.scalars(select(ExtractedFact).where(ExtractedFact.organization_id == organization_id, ExtractedFact.campaign_id == campaign.id, ExtractedFact.fact_type.in_(["percentage", "currency", "date", "claim"]))).all():
                    db.delete(old_fact)
            scan.asset_versions = {asset.id: asset.version for asset in assets}
            scan.rules_version = expected_rules_version
            findings: list[Finding] = []
            extracted_facts: list[ExtractedFact] = []
            publish_date = reference_date
            organization = db.scalar(select(Organization).where(Organization.id == organization_id))
            llm_client = None
            if organization and organization.llm_processing_allowed:
                try:
                    llm_client = get_llm_client(organization)
                    scan.llm_vendor = llm_client.vendor
                    scan.model_version = llm_client.model
                except Exception:
                    # Any unavailable provider is handled as human verification below.
                    llm_client = None
            scan.prompt_version = JUDGEMENT_PROMPT_VERSION
            # Persist immutable scan inputs before refreshing cancellation state in the loop.
            db.commit()
            scan_started = time.monotonic()
            judgement_count = 0
            for asset_index, asset in enumerate(assets):
                if time.monotonic() - scan_started > get_settings().scan_timeout_seconds:
                    raise TimeoutError("Campaign scan exceeded its configured time limit.")
                if asset.id in scan.completed_asset_ids:
                    continue
                db.refresh(scan)
                if scan.cancel_requested or scan.status == "cancelled":
                    scan.status = "cancelled"
                    scan.completed_at = datetime.now(UTC)
                    db.add(AuditEvent(organization_id=organization_id, actor_user_id=scan.requested_by, action="campaign.scan_cancelled", entity_type="scan", entity_id=scan.id, details={"progress": scan.progress}))
                    db.commit()
                    return
                if scan.status != "running":
                    return
                content = asset.extracted_text or asset.text_content or ""
                folded = content.casefold()
                scheduled = publish_date
                for offer_rule, offer_passage, offer_source in offer_rows:
                    if offer_rule.channel and offer_rule.channel.casefold() != asset.channel.casefold():
                        continue
                    params = offer_rule.parameters or {}
                    language = str(params.get("language", "")).strip()
                    if language and language.casefold() != asset.language.casefold():
                        continue
                    offer_match = None
                    if offer_rule.rule_type == "discount_percent":
                        expected = float(params.get("percent", -1))
                        offer_match = next((match for match in PERCENT_RE.finditer(content) if abs(float(match.group(1)) - expected) <= 0.001), None)
                    elif offer_rule.rule_type == "offer_name":
                        name = str(params.get("value", "")).strip()
                        offer_match = re.search(re.escape(name), content, re.IGNORECASE) if name else None
                    valid_froms = [value for value in (offer_rule.valid_from, offer_source.effective_from) if value]
                    valid_tos = [value for value in (offer_rule.valid_to, offer_source.effective_to) if value]
                    valid_from = max(valid_froms) if valid_froms else None
                    valid_to = min(valid_tos) if valid_tos else None
                    not_yet_valid = bool(valid_from and scheduled < valid_from)
                    expired = bool(valid_to and scheduled > valid_to)
                    if offer_match and (not_yet_valid or expired):
                        boundary = valid_from.isoformat() if not_yet_valid else valid_to.isoformat()
                        description = "not valid yet" if not_yet_valid else "expired"
                        validity = "not_yet_valid" if not_yet_valid else "expired"
                        findings.append(_finding(scan=scan, asset=asset, rule=offer_rule, passage=offer_passage, finding_type="offer_validity", severity="warning", text=content, start=offer_match.start(), end=offer_match.end(), quoted_excerpt=offer_passage.text, confidence=1.0, suggested_fix=f"The offer appears {description} for {scheduled.isoformat()}; review its approved validity through {boundary}.", flagged_region={"validity": validity, "scheduled_date": scheduled.isoformat(), "valid_from": valid_from.isoformat() if valid_from else None, "valid_to": valid_to.isoformat() if valid_to else None}))
                discount_evidence = next(((rule, passage) for rule, passage, _source in rows if rule.rule_type == "discount_percent"), None)
                for match in PERCENT_RE.finditer(content):
                    value = f"{float(match.group(1)):g}%"
                    extracted_facts.append(ExtractedFact(organization_id=organization_id, campaign_id=campaign.id, asset_id=asset.id, fact_type="percentage", value=value, asset_location={"start": match.start(), "end": match.end(), "text": match.group()}, source_passage_id=discount_evidence[1].id if discount_evidence else None))
                    if not discount_evidence:
                        findings.append(_finding(scan=scan, asset=asset, rule=None, passage=None, finding_type="fact_without_approved_evidence", severity="info", text=content, start=match.start(), end=match.end(), quoted_excerpt=None, confidence=0.0, suggested_fix="Needs human verification: no approved source supports this extracted percentage.", flagged_region={"verdict": "Needs human verification", "fact_type": "percentage", "normalized_value": value}))
                for fact_type, pattern in (("currency", CURRENCY_RE), ("date", DATE_RE)):
                    for match in pattern.finditer(content):
                        normalized = _normalize_currency(match.group()) if fact_type == "currency" else _normalize_date(match.group())
                        candidates = retrieve_top_passages(db, organization_id, normalized, reference_date)
                        cited = next((candidate for candidate in candidates if normalized.casefold() in candidate["text"].casefold()), None)
                        extracted_facts.append(ExtractedFact(organization_id=organization_id, campaign_id=campaign.id, asset_id=asset.id, fact_type=fact_type, value=normalized, asset_location={"start": match.start(), "end": match.end(), "text": match.group()}, source_passage_id=cited["passage_id"] if cited else None))
                        if not cited:
                            findings.append(_finding(scan=scan, asset=asset, rule=None, passage=None, finding_type="fact_without_approved_evidence", severity="info", text=content, start=match.start(), end=match.end(), quoted_excerpt=None, confidence=0.0, suggested_fix=f"Needs human verification: no approved source supports this extracted {fact_type}.", flagged_region={"verdict": "Needs human verification", "fact_type": fact_type, "normalized_value": normalized}))
                for rule, passage, _source in rows:
                    if rule.channel and rule.channel.casefold() != asset.channel.casefold():
                        continue
                    params = rule.parameters or {}
                    rule_language = str(params.get("language", "")).strip()
                    if rule_language and rule_language.casefold() != asset.language.casefold():
                        continue
                    rule_type = rule.rule_type
                    if rule_type == "banned_phrase":
                        value = str(params.get("value", "")).strip()
                        match = re.search(re.escape(value), content, re.IGNORECASE) if value else None
                        if match:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="high", text=content, start=match.start(), end=match.end(), quoted_excerpt=passage.text, confidence=1.0, suggested_fix="Remove or replace the flagged phrase, then rescan."))
                    elif rule_type == "required_disclaimer":
                        value = str(params.get("value", "")).strip()
                        if value and value.casefold() not in folded:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="high", text=None, start=None, end=None, quoted_excerpt=passage.text, confidence=1.0, suggested_fix="Add the required disclaimer from the cited approved passage."))
                    elif rule_type == "discount_percent":
                        expected = float(params.get("percent", -1))
                        percent_matches = list(PERCENT_RE.finditer(content))
                        for match in percent_matches:
                            if abs(float(match.group(1)) - expected) > 0.001:
                                findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="high", text=content, start=match.start(), end=match.end(), quoted_excerpt=passage.text, confidence=1.0, suggested_fix=f"Check this value against the approved {expected:g}% offer in the cited passage."))
                        if not percent_matches:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="medium", text=None, start=None, end=None, quoted_excerpt=passage.text, confidence=0.95, suggested_fix=f"Confirm the approved {expected:g}% offer is represented correctly in this asset."))
                    elif rule_type == "offer_name":
                        value = str(params.get("value", "")).strip()
                        if value and value.casefold() not in folded:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="medium", text=None, start=None, end=None, quoted_excerpt=passage.text, confidence=0.9, suggested_fix="Confirm the asset uses the approved offer name shown in the cited passage."))
                    elif rule_type == "channel_length_limit":
                        channel = str(params.get("channel", ""))
                        limit = int(params.get("max_characters", 0))
                        if channel.casefold() == asset.channel.casefold() and limit > 0 and len(content) > limit:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="medium", text=content, start=limit, end=len(content), quoted_excerpt=passage.text, confidence=1.0, suggested_fix=f"Reduce this asset to {limit} characters or fewer."))
                    elif rule_type in {"valid_from", "valid_until"}:
                        expected = str(params.get("date", ""))
                        scheduled = publish_date if campaign.planned_publish_date else (campaign.starts_at if rule_type == "valid_from" else campaign.ends_at)
                        outside_window = bool(expected) and scheduled is not None and ((rule_type == "valid_from" and scheduled < date.fromisoformat(expected)) or (rule_type == "valid_until" and scheduled > date.fromisoformat(expected)))
                        if outside_window:
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="high", text=None, start=None, end=None, quoted_excerpt=passage.text, confidence=1.0, suggested_fix=f"Review the campaign date against the approved {expected} date."))
                    elif rule_type == "approved_logo" and asset.asset_type == "image":
                        matching = [item for item in asset.logo_matches if item.get("source_id") == passage.source_id]
                        if matching and not any(item.get("matched") for item in matching):
                            findings.append(_finding(scan=scan, asset=asset, rule=rule, passage=passage, finding_type=rule_type, severity="medium", text=None, start=None, end=None, quoted_excerpt=passage.text, confidence=0.5, suggested_fix="Compare this image with the approved logo manually; perceptual matching is a prototype."))

                # Judgement checks are opt-in per workspace and can only cite retrieved approved evidence.
                claim_sentences = list(re.finditer(r"[^.!?\n]+(?:[.!?]|$)", content))
                for sentence in claim_sentences:
                    if time.monotonic() - scan_started > get_settings().scan_timeout_seconds:
                        raise TimeoutError("Campaign scan exceeded its configured time limit.")
                    db.refresh(scan)
                    if scan.cancel_requested or scan.status == "cancelled":
                        scan.status = "cancelled"
                        scan.completed_at = datetime.now(UTC)
                        db.commit()
                        return
                    if scan.status != "running":
                        return
                    claim = sentence.group().strip()
                    if not claim or not CLAIM_CUES.search(claim):
                        continue
                    judgement_count += 1
                    retrieved = retrieve_top_passages(db, organization_id, claim, reference_date)
                    started = time.monotonic()
                    result = None
                    latency_ms = 0
                    if llm_client and retrieved and judgement_count <= get_settings().scan_max_claims:
                        try:
                            raw = llm_client.judge(JUDGEMENT_TASK_INSTRUCTIONS, retrieved, claim)
                            result = parse_judgement(raw, asset_text=claim, retrieved=retrieved)
                        except Exception:
                            result = None
                        latency_ms = round((time.monotonic() - started) * 1000)
                    if result and result.verdict == "compliant":
                        verdict = "compliant"
                    elif result and result.verdict == "breach":
                        source_passage = db.scalar(select(SourcePassage).where(SourcePassage.organization_id == organization_id, SourcePassage.source_id == result.source_id, SourcePassage.id.in_([item["passage_id"] for item in retrieved])))
                        if not source_passage:
                            result = None
                        else:
                            flagged_match = re.search(re.escape(result.flagged_text or ""), claim, re.IGNORECASE)
                            if not flagged_match:
                                result = None
                            else:
                                findings.append(_finding(scan=scan, asset=asset, rule=None, passage=source_passage, finding_type="judgement_claim", severity="medium", text=content, start=sentence.start() + flagged_match.start(), end=sentence.start() + flagged_match.end(), quoted_excerpt=result.quoted_excerpt, confidence=result.confidence, suggested_fix=result.suggested_fix or "Review this claim with the approved passage and a human reviewer.", flagged_region={"rationale": result.rationale, "verdict": result.verdict}))
                            verdict = "breach"
                    if not result or (result and result.verdict == "insufficient_evidence"):
                        findings.append(_finding(scan=scan, asset=asset, rule=None, passage=None, finding_type="needs_human_verification", severity="info", text=content, start=sentence.start(), end=sentence.end(), quoted_excerpt=None, confidence=0.0, suggested_fix="Needs human verification: no validated approved-evidence judgement is available.", flagged_region={"verdict": "Needs human verification"}))
                        verdict = "insufficient_evidence"
                    claim_source = next((item for item in retrieved if result and item["source_id"] == result.source_id), None)
                    extracted_facts.append(ExtractedFact(organization_id=organization_id, campaign_id=campaign.id, asset_id=asset.id, fact_type="claim", value=claim, asset_location={"start": sentence.start(), "end": sentence.end(), "text": claim}, source_passage_id=claim_source["passage_id"] if claim_source else None))
                    if not claim_source:
                        findings.append(_finding(scan=scan, asset=asset, rule=None, passage=None, finding_type="fact_without_approved_evidence", severity="info", text=content, start=sentence.start(), end=sentence.end(), quoted_excerpt=None, confidence=0.0, suggested_fix="Needs human verification: no validated approved source is linked to this claim.", flagged_region={"verdict": "Needs human verification", "fact_type": "claim"}))
                    db.add(AuditEvent(organization_id=organization_id, actor_user_id=scan.requested_by, action="scan.judgement_checked", entity_type="scan", entity_id=scan.id, details={"asset_id": asset.id, "verdict": verdict, "prompt_version": scan.prompt_version, "model": scan.model_version, "vendor": scan.llm_vendor, "retrieved_passage_ids": [item["passage_id"] for item in retrieved], "latency_ms": latency_ms}))
                scan.completed_asset_ids = [*scan.completed_asset_ids, asset.id]
                scan.progress = round(len(scan.completed_asset_ids) / len(assets) * 100)
                db.add_all(extracted_facts)
                db.add_all(findings)
                db.commit()

            # Compare normalized facts across channels. Conflicts prompt review and are never labelled a breach.
            fact_groups: dict[str, list[tuple[ExtractedFact, Asset]]] = {}
            current_facts = db.execute(select(ExtractedFact, Asset).join(Asset, (Asset.organization_id == ExtractedFact.organization_id) & (Asset.id == ExtractedFact.asset_id)).where(ExtractedFact.organization_id == organization_id, ExtractedFact.campaign_id == campaign.id, ExtractedFact.asset_id.in_(expected_asset_versions), ExtractedFact.fact_type.in_(["percentage", "currency", "date", "claim"]))).all()
            for fact, asset in current_facts:
                fact_groups.setdefault(fact.fact_type, []).append((fact, asset))
            for old in db.scalars(select(Finding).where(Finding.organization_id == organization_id, Finding.scan_id == scan.id, Finding.finding_type == "campaign_fact_conflict")).all():
                db.delete(old)
            for fact_type, facts in fact_groups.items():
                values = {fact.value.casefold() for fact, _asset in facts}
                asset_ids = {asset.id for _fact, asset in facts}
                if len(values) < 2 or len(asset_ids) < 2:
                    continue
                for fact, asset in facts:
                    other_facts = [{"asset_id": other_asset.id, "channel": other_asset.channel, "value": other.value, "excerpt": other.asset_location.get("text", "")} for other, other_asset in facts if other_asset.id != asset.id and other.value.casefold() != fact.value.casefold()]
                    if other_facts:
                        source_passage = db.scalar(select(SourcePassage).where(SourcePassage.organization_id == organization_id, SourcePassage.id == fact.source_passage_id)) if fact.source_passage_id else None
                        findings.append(_finding(scan=scan, asset=asset, rule=None, passage=source_passage, finding_type="campaign_fact_conflict", severity="warning", text=asset.extracted_text or asset.text_content or "", start=(fact.asset_location or {}).get("start"), end=(fact.asset_location or {}).get("end"), quoted_excerpt=source_passage.text if source_passage else " | ".join(item["excerpt"] for item in other_facts[:3]), confidence=0.0, suggested_fix="Review the differing values across campaign assets. This comparison needs human verification.", flagged_region={"fact_type": fact_type, "normalized_value": fact.value, "conflicting_assets": other_facts[:3], "verdict": "Needs human verification"}))

            db.add_all(findings)
            scan.status = "completed"
            scan.completed_at = datetime.now(UTC)
            db.add(AuditEvent(organization_id=organization_id, actor_user_id=scan.requested_by, action="campaign.scan_completed", entity_type="scan", entity_id=scan.id, details={"finding_count": len(findings), "asset_count": len(assets), "checks": "deterministic-rules-and-cross-asset-percentage-comparison"}))
            db.commit()
        except Exception:
            db.rollback()
            failed = db.scalar(select(Scan).where(Scan.organization_id == organization_id, Scan.id == scan_id))
            if failed:
                failed.status = "failed"
                failed.completed_at = datetime.now(UTC)
                db.add(AuditEvent(organization_id=organization_id, actor_user_id=failed.requested_by, action="campaign.scan_failed", entity_type="scan", entity_id=failed.id, details={"reason": "Scan could not be completed."}))
                db.commit()
            raise

