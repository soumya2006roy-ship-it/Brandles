from datetime import UTC, date, datetime

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.db.models import Asset, BrandGuidelineSource, Campaign, Finding, Membership, Organization, Rule, Scan, SourcePassage, User
from app.campaigns import scans
from app.checks.judgement import parse_judgement


def _database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(scans, "SessionLocal", factory)
    return factory, engine


def _campaign_records(db, *, first_text: str, second_text: str | None = None, with_rule: bool = True, rule_type: str = "discount_percent", parameters=None, starts_at=None, ends_at=None):
    user = User(email="creator@example.com", email_normalized="creator@example.com", display_name="Creator", password_hash="test", email_verified_at=datetime.now(UTC))
    db.add(user)
    db.flush()
    org = Organization(name="Example", industry="Retail", official_email="team@example.com", website="https://example.com", contact_person="Creator", verification_status="approved", created_by=user.id)
    db.add(org)
    db.flush()
    campaign = Campaign(organization_id=org.id, name="Spring", channels=["Instagram", "Email"], starts_at=starts_at if starts_at is not None else date.today(), ends_at=ends_at if ends_at is not None else date.today(), language="en", status="draft", created_by=user.id)
    db.add(campaign)
    source = passage = rule = None
    if with_rule:
        source = BrandGuidelineSource(organization_id=org.id, title="Offer sheet", document_ref="source.txt", original_filename="source.txt", content_type="text/plain", sha256="abc", size_bytes=20, version=1, status="approved", effective_from=date.today(), created_by=user.id, approved_by=user.id, approved_at=datetime.now(UTC))
        db.add(source)
        db.flush()
        passage = SourcePassage(organization_id=org.id, source_id=source.id, text="The approved offer is 20% off.", page_number=1)
        db.add(passage)
        db.flush()
        rule = Rule(organization_id=org.id, rule_type=rule_type, parameters=parameters if parameters is not None else {"percent": 20}, source_passage_id=passage.id, status="active", created_by=user.id)
        db.add(rule)
    db.flush()
    assets = [Asset(organization_id=org.id, campaign_id=campaign.id, asset_type="text", channel="Instagram", language="en", asset_group_id="a1", version=1, current=True, content_type="text/plain", sha256="a", size_bytes=len(first_text), malware_status="not_applicable", extraction_status="complete", text_content=first_text, extracted_text=first_text, created_by=user.id)]
    if second_text is not None:
        assets.append(Asset(organization_id=org.id, campaign_id=campaign.id, asset_type="text", channel="Email", language="en", asset_group_id="a2", version=1, current=True, content_type="text/plain", sha256="b", size_bytes=len(second_text), malware_status="not_applicable", extraction_status="complete", text_content=second_text, extracted_text=second_text, created_by=user.id))
    db.add_all(assets)
    db.flush()
    scan = Scan(organization_id=org.id, campaign_id=campaign.id, status="queued", requested_by=user.id)
    db.add(scan)
    db.commit()
    return org, campaign, assets, scan, passage


def test_scan_links_exact_mismatch_to_approved_passage(monkeypatch):
    factory, engine = _database(monkeypatch)
    try:
        with factory() as db:
            org, _campaign, _assets, scan, passage = _campaign_records(db, first_text="Save 30% today.")
            scan_id = scan.id
            passage_id = passage.id
            org_id = org.id
        scans.execute_campaign_scan(org_id, scan_id)
        with factory() as db:
            result = db.scalar(select(Scan).where(Scan.id == scan_id))
            finding = db.scalar(select(Finding).where(Finding.scan_id == scan_id))
            assert result.status == "completed"
            assert finding.finding_type == "discount_percent"
            assert finding.source_passage_id == passage_id
            assert finding.flagged_region["text"] == "30%"
            assert finding.quoted_excerpt == "The approved offer is 20% off."
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_campaign_percentage_difference_is_human_verification_not_a_breach(monkeypatch):
    factory, engine = _database(monkeypatch)
    try:
        with factory() as db:
            org, _campaign, _assets, scan, _passage = _campaign_records(db, first_text="Instagram: 20% off", second_text="Email: 30% off", with_rule=False)
            org_id, scan_id = org.id, scan.id
        scans.execute_campaign_scan(org_id, scan_id)
        with factory() as db:
            rows = db.scalars(select(Finding).where(Finding.scan_id == scan_id)).all()
            prompts = [row for row in rows if row.finding_type == "campaign_fact_conflict"]
            assert len(prompts) == 2
            assert all(row.confidence == 0 for row in prompts)
            assert all(row.flagged_region["verdict"] == "Needs human verification" for row in prompts)
            assert all(row.source_passage_id is None for row in prompts)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize(("rule_type", "parameters", "text", "starts_at", "ends_at", "expected"), [
    ("banned_phrase", {"value": "miracle"}, "A miracle cream", None, None, True),
    ("banned_phrase", {"value": "miracle"}, "Everyday moisturiser", None, None, False),
    ("required_disclaimer", {"value": "terms apply"}, "Offer available today", None, None, True),
    ("required_disclaimer", {"value": "terms apply"}, "Offer available; terms apply", None, None, False),
    ("discount_percent", {"percent": 20}, "Save 30% today", None, None, True),
    ("discount_percent", {"percent": 20}, "Save 20% today", None, None, False),
    ("offer_name", {"value": "Glow Serum"}, "Glow Serum offer", None, None, False),
    ("offer_name", {"value": "Glow Serum"}, "Spring offer", None, None, True),
    ("channel_length_limit", {"channel": "Instagram", "max_characters": 12}, "This caption is too long", None, None, True),
    ("channel_length_limit", {"channel": "Instagram", "max_characters": 40}, "Short caption", None, None, False),
    ("valid_from", {"date": "2030-01-02"}, "Offer text", date(2030, 1, 1), date(2030, 1, 5), True),
    ("valid_from", {"date": "2030-01-02"}, "Offer text", date(2030, 1, 3), date(2030, 1, 5), False),
    ("valid_until", {"date": "2030-01-02"}, "Offer text", date(2030, 1, 1), date(2030, 1, 3), True),
    ("valid_until", {"date": "2030-01-02"}, "Offer text", date(2030, 1, 1), date(2030, 1, 2), False),
    ("banned_phrase", {"value": "miracle", "language": "fr"}, "miracle cream", None, None, False),
])
def test_exact_rule_positive_and_negative_cases(monkeypatch, rule_type, parameters, text, starts_at, ends_at, expected):
    factory, engine = _database(monkeypatch)
    try:
        with factory() as db:
            org, _campaign, _assets, scan, _passage = _campaign_records(db, first_text=text, rule_type=rule_type, parameters=parameters, starts_at=starts_at, ends_at=ends_at)
            org_id, scan_id = org.id, scan.id
        scans.execute_campaign_scan(org_id, scan_id)
        with factory() as db:
            findings = db.scalars(select(Finding).where(Finding.scan_id == scan_id, Finding.finding_type == rule_type)).all()
            assert bool(findings) is expected
            if findings:
                assert findings[0].confidence is not None
                assert findings[0].source_passage_id is not None
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize("matched,expected", [(True, False), (False, True)])
def test_approved_logo_rule_positive_and_negative_cases(monkeypatch, matched, expected):
    factory, engine = _database(monkeypatch)
    try:
        with factory() as db:
            org, campaign, _assets, scan, passage = _campaign_records(db, first_text="", rule_type="approved_logo", parameters={"version": "primary-v2"})
            logo = Asset(organization_id=org.id, campaign_id=campaign.id, asset_type="image", channel="Instagram", language="en", asset_group_id="logo", version=1, current=True, content_type="image/png", sha256="logo", size_bytes=10, malware_status="not_configured", extraction_status="not_configured", logo_matches=[{"source_id": passage.source_id, "matched": matched, "logo_version": "primary-v2"}], created_by=scan.requested_by)
            db.add(logo)
            db.commit()
            org_id, scan_id = org.id, scan.id
        scans.execute_campaign_scan(org_id, scan_id)
        with factory() as db:
            findings = db.scalars(select(Finding).where(Finding.scan_id == scan_id, Finding.finding_type == "approved_logo")).all()
            assert bool(findings) is expected
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_judgement_requires_real_citation_and_caps_confidence():
    retrieved = [{"source_id": "source-1", "text": "The cream keeps skin hydrated."}]
    raw = {"verdict": "breach", "flagged_text": "cures acne", "source_id": "source-1", "quoted_excerpt": "The cream keeps skin hydrated.", "rationale": "The cited claim differs.", "confidence": 0.99, "suggested_fix": "Review wording."}
    parsed = parse_judgement(raw, asset_text="Our cream cures acne.", retrieved=retrieved)
    assert parsed.confidence == 0.95
    with pytest.raises(ValueError, match="quoted excerpt"):
        parse_judgement({**raw, "quoted_excerpt": "The product cures acne."}, asset_text="Our cream cures acne.", retrieved=retrieved)
