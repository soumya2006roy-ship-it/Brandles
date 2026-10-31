"""Create isolated, clearly labelled Brand Health demo records (development only).

Example: python scripts/seed_brand_health.py --email owner@example.com --confirm-demo-data
"""

import argparse
import secrets
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, Finding, Membership, Organization, Review, Rule, Scan, SourcePassage, User


DEMO_ORG_NAME = "BrandLens Brand Health Demo [DEMO DATA]"


def seed(email: str) -> tuple[bool, str]:
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("Demo seed refuses to run when APP_ENV=production.")
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email_normalized == email.strip().lower(), User.is_active.is_(True)))
        if not owner:
            raise RuntimeError("The supplied email must belong to an existing active account.")
        existing = db.scalar(select(Organization).where(Organization.created_by == owner.id, Organization.name == DEMO_ORG_NAME, Organization.deleted_at.is_(None)))
        if existing:
            return False, existing.id

        org = Organization(name=DEMO_ORG_NAME, industry="Consumer products", official_email="demo@example.test", website="https://brandlens.example.test", contact_person="Demo workspace", verification_status="approved", created_by=owner.id)
        db.add(org)
        db.flush()
        db.add(Membership(organization_id=org.id, user_id=owner.id, role="admin"))

        reviewer_ids = []
        for index in range(2):
            reviewer_email = f"brand-health-demo-reviewer-{index + 1}@example.test"
            reviewer = db.scalar(select(User).where(User.email_normalized == reviewer_email))
            if not reviewer:
                reviewer = User(email=reviewer_email, email_normalized=reviewer_email, display_name=f"Demo Reviewer {index + 1}", password_hash=hash_password(secrets.token_urlsafe(32)), is_active=False)
                db.add(reviewer)
                db.flush()
            reviewer_ids.append(reviewer.id)
            db.add(Membership(organization_id=org.id, user_id=reviewer.id, role="reviewer"))

        source = BrandGuidelineSource(organization_id=org.id, title="[DEMO] Spring campaign guidance", document_ref="demo://brand-health/source", original_filename="demo-guidance.txt", content_type="text/plain", sha256="demo-seed", size_bytes=280, version=1, status="approved", effective_from=date.today() - timedelta(days=90), created_by=owner.id, approved_by=owner.id, approved_at=datetime.now(UTC))
        db.add(source)
        db.flush()
        passages = [SourcePassage(organization_id=org.id, source_id=source.id, text=text, page_number=page, location_label=f"Demo page {page}") for page, text in enumerate([
            "Approved spring skincare offer: 20% off selected moisturisers. Terms apply.",
            "Use the current approved BrandLens wordmark. Do not use retired identity artwork.",
            "Do not claim a product cures or treats a medical condition without approved substantiation.",
        ], start=1)]
        db.add_all(passages)
        db.flush()
        rule_types = ["discount_percent", "approved_logo", "required_disclaimer", "unsupported_claim"]
        rules = []
        for index, kind in enumerate(rule_types):
            params = {"percent": 20} if kind == "discount_percent" else {"version": "current"} if kind == "approved_logo" else {"value": "Terms apply"} if kind == "required_disclaimer" else {"value": "medical claim substantiation"}
            rule = Rule(organization_id=org.id, rule_type=kind, parameters=params, source_passage_id=passages[index % len(passages)].id, status="active", created_by=owner.id)
            db.add(rule)
            rules.append(rule)
        db.flush()

        campaigns: list[tuple[Campaign, list[Asset]]] = []
        campaign_names = ["Spring skincare launch", "Summer essentials", "Member appreciation", "Winter hydration"]
        channels = ["Instagram", "LinkedIn", "Email", "Poster"]
        today = date.today()
        for index, name in enumerate(campaign_names):
            campaign = Campaign(organization_id=org.id, name=f"[DEMO] {name}", channels=[channels[index]], starts_at=today - timedelta(days=59), ends_at=today + timedelta(days=30), language="en", status="in_review", created_by=owner.id)
            db.add(campaign)
            db.flush()
            assets = []
            for asset_index in range(2):
                text = f"{name}: Save 20% on selected skincare. Terms apply."
                asset = Asset(organization_id=org.id, campaign_id=campaign.id, asset_type="text", channel=channels[index], language="en", asset_group_id=f"demo-{index}-{asset_index}", version=1, current=True, content_type="text/plain", sha256=f"demo-{index}-{asset_index}", size_bytes=len(text), malware_status="not_applicable", extraction_status="complete", text_content=text, extracted_text=text, created_by=owner.id)
                db.add(asset)
                assets.append(asset)
            db.flush()
            campaigns.append((campaign, assets))

        start_day = today - timedelta(days=59)
        created_count = 0
        for day_number in range(60):
            scan_date = start_day + timedelta(days=day_number)
            for campaign_index, (campaign, assets) in enumerate(campaigns):
                created_at = datetime.combine(scan_date, datetime.min.time(), tzinfo=UTC) + timedelta(hours=9 + campaign_index)
                scan = Scan(organization_id=org.id, campaign_id=campaign.id, status="completed", rules_version="demo-rules-v1", asset_versions={asset.id: asset.version for asset in assets}, progress=100, completed_asset_ids=[asset.id for asset in assets], requested_by=owner.id, created_at=created_at, completed_at=created_at + timedelta(minutes=2 + day_number % 9))
                db.add(scan)
                db.flush()
                count = 1 + ((day_number + campaign_index) % 2)
                for finding_index in range(count):
                    choice = (day_number + campaign_index + finding_index) % len(rules)
                    rule = rules[choice]
                    pattern = (day_number + campaign_index + finding_index) % 7
                    status = "dismissed" if pattern == 0 else "resolved" if pattern in {1, 2, 3} else "open" if pattern in {4, 5} else "clarification_requested"
                    severity = ("critical", "high", "medium", "low")[(day_number + finding_index) % 4]
                    text = ["30% off", "retired logo", "Terms apply", "cures acne"][choice]
                    finding = Finding(organization_id=org.id, scan_id=scan.id, asset_id=assets[finding_index % len(assets)].id, finding_type=rule.rule_type, severity=severity, status=status, flagged_region={"text": text, "start": 0, "end": len(text)}, rule_id=rule.id, source_passage_id=rule.source_passage_id, quoted_excerpt=passages[choice % len(passages)].text, confidence=0.82, suggested_fix="Check the current approved source and update the campaign text.", resolution="Reviewed against approved guidance." if status == "resolved" else None, dismissal_reason="Demo reviewer confirmed the flag was not applicable." if status == "dismissed" else None, created_at=created_at + timedelta(minutes=3 + finding_index))
                    db.add(finding)
                    db.flush()
                    if status in {"resolved", "dismissed"}:
                        action = "finding.dismissed" if status == "dismissed" else "finding.resolved"
                        db.add(AuditEvent(organization_id=org.id, actor_user_id=owner.id, action=action, entity_type="finding", entity_id=finding.id, details={"demo_seed": True, "finding_type": rule.rule_type, "resolution_kind": "override" if status == "resolved" and day_number % 5 == 0 else "standard"}, created_at=created_at + timedelta(hours=1 + day_number % 8)))
                    created_count += 1

                if day_number % 3 == 0:
                    reviewer_id = reviewer_ids[(day_number + campaign_index) % len(reviewer_ids)]
                    decision = ("approved", "rejected", "changes_requested")[(day_number // 3 + campaign_index) % 3]
                    # Review.submission_id is a UUID-sized field; use a stable
                    # UUID per seeded scan instead of concatenating two UUIDs.
                    submission_id = str(uuid4())
                    db.add(Review(organization_id=org.id, asset_id=assets[0].id, asset_version=1, submission_id=submission_id, submitted_by_user_id=owner.id, reviewer_user_id=reviewer_id, scan_id=scan.id, decision=decision, comment="Demo review history.", created_at=created_at + timedelta(hours=2 + day_number % 12)))
        db.add(AuditEvent(organization_id=org.id, actor_user_id=owner.id, action="demo.brand_health_seeded", entity_type="demo_seed", entity_id=org.id, details={"demo_seed": True, "campaigns": len(campaigns), "days": 60, "scans": 240, "findings": created_count}))
        db.commit()
        return True, org.id


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a clearly labelled 60-day Brand Health demo workspace. Never use in production.")
    parser.add_argument("--email", required=True, help="Existing account that will own the isolated demo workspace")
    parser.add_argument("--confirm-demo-data", action="store_true", help="Explicitly confirm that demo records should be written")
    args = parser.parse_args()
    if not args.confirm_demo_data:
        parser.error("Pass --confirm-demo-data to write the isolated demo workspace.")
    created, org_id = seed(args.email)
    print(("Created" if created else "Already seeded; left unchanged") + f" demo workspace {org_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
