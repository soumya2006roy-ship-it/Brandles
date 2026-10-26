"""Seed the proposal's fictional skincare scenario for the public read-only sandbox."""

import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.db import SessionLocal
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, Organization, Rule, SourcePassage, User
from app.campaigns.scans import execute_campaign_scan


def main() -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(Organization).where(Organization.is_sample.is_(True)))
        if existing:
            print(f"Sample workspace already exists ({existing.id}); no changes made.")
            return 0
        user = User(email="sample-workspace@brandlens.invalid", email_normalized="sample-workspace@brandlens.invalid", display_name="BrandLens sample seed", password_hash="!read-only-sample-account", email_verified_at=datetime.now(UTC))
        db.add(user)
        db.flush()
        organization = Organization(name="BrandLens fictional skincare sample", industry="Skincare", official_email=user.email, website="https://example.invalid", contact_person="Sample workspace", verification_status="approved", llm_processing_allowed=False, is_sample=True, created_by=user.id)
        db.add(organization)
        db.flush()
        campaign = Campaign(organization_id=organization.id, name="Hydration campaign · sample", channels=["Instagram", "Email", "Poster"], starts_at=date(2026, 11, 15), ends_at=date(2026, 11, 30), planned_publish_date=datetime(2026, 11, 20, 12, 0, tzinfo=UTC), language="en", status="draft", created_by=user.id)
        db.add(campaign)
        db.flush()
        source_text = "Approved product wording: The moisturiser helps to keep the skin hydrated. Current offer: 20% off until 30 November 2026."
        source = BrandGuidelineSource(organization_id=organization.id, title="Fictional skincare product and offer sheet", family_id="sample-skin-care-guidance", original_filename="sample-approved-guidance.txt", content_type="text/plain", document_ref="sample-workspace/approved-guidance.txt", sha256="sample-only", size_bytes=len(source_text), version=1, status="approved", effective_from=date(2026, 1, 1), effective_to=date(2026, 11, 30), created_by=user.id, approved_by=user.id, approved_at=datetime.now(UTC))
        db.add(source)
        db.flush()
        passage = SourcePassage(organization_id=organization.id, source_id=source.id, text=source_text, location_label="Sample approved guidance", start_offset=0, end_offset=len(source_text))
        db.add(passage)
        db.flush()
        rules = [
            Rule(organization_id=organization.id, rule_type="discount_percent", parameters={"percent": 20}, source_passage_id=passage.id, valid_to=date(2026, 11, 30), status="active", created_by=user.id),
            Rule(organization_id=organization.id, rule_type="banned_phrase", parameters={"value": "cures acne in 24 hours"}, source_passage_id=passage.id, status="active", created_by=user.id),
        ]
        db.add_all(rules)
        seed_assets = [
            ("Instagram", "instagram", "Our moisturiser cures acne in 24 hours."),
            ("Email", "email", "Take 30% off through 30 November 2026."),
            ("Poster", "poster", "Our moisturiser helps to keep the skin hydrated."),
        ]
        for channel, group_id, content in seed_assets:
            db.add(Asset(organization_id=organization.id, campaign_id=campaign.id, asset_type="text", channel=channel, language="en", asset_group_id=group_id, version=1, current=True, content_type="text/plain", sha256=f"sample-{group_id}", size_bytes=len(content), malware_status="not_applicable", extraction_status="complete", text_content=content, extracted_text=content, created_by=user.id))
        db.add(AuditEvent(organization_id=organization.id, actor_user_id=user.id, action="sample_workspace.seeded", entity_type="organization", entity_id=organization.id, details={"fictional": True, "read_only_public_view": True}))
        db.commit()
        organization_id, campaign_id = organization.id, campaign.id
    scan_id = ""
    with SessionLocal() as db:
        from app.db.models import Scan
        scan = Scan(organization_id=organization_id, campaign_id=campaign_id, status="queued", requested_by=user.id, rules_version="pending")
        db.add(scan)
        db.commit()
        scan_id = scan.id
    execute_campaign_scan(organization_id, scan_id)
    print(f"Seeded read-only sample workspace {organization_id}; campaign scan {scan_id} completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
