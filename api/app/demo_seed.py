"""Provision the public, fictional judge-demo workspace for the app demo."""

from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.db.models import (
    Asset,
    AuditEvent,
    BrandGuidelineSource,
    Campaign,
    Membership,
    Organization,
    Review,
    Rule,
    Scan,
    SourcePassage,
    User,
)


DEMO_ORGANIZATION = "[DEMO] BrandLens Judge Workspace"
DEMO_ACCOUNTS = (
    {
        "email": "judge-admin@brandlens.example.test",
        "password": "JudgeAdmin2026!",
        "name": "Judge Demo Admin",
        "role": "admin",
    },
    {
        "email": "judge-creator@brandlens.example.test",
        "password": "JudgeCreator2026!",
        "name": "Judge Demo Creator",
        "role": "creator",
    },
    {
        "email": "judge-reviewer@brandlens.example.test",
        "password": "JudgeReviewer2026!",
        "name": "Judge Demo Reviewer",
        "role": "reviewer",
    },
)

SOURCE_TEXTS = (
    "[DEMO] Product guidance: describe the lotion as helping skin feel hydrated. Do not claim it treats or cures a medical condition.",
    "[DEMO] Offer guidance: 20% off selected moisturizers. The words 'Terms apply' must appear in each offer asset.",
    "[DEMO] Identity guidance: use the current approved Demo Botanicals wordmark and approved brand colors.",
)

CAMPAIGNS = (
    {
        "name": "[DEMO] Summer hydration offer",
        "channels": ["Instagram", "Email"],
        "status": "draft",
        "assets": (
            ("summer-instagram", "Instagram", "[DEMO] Demo Botanicals lotion helps skin feel hydrated. Save 30% on selected moisturizers."),
            ("summer-email", "Email", "[DEMO] Save 30% on selected moisturizers. Terms apply."),
        ),
        "scan": True,
        "review": False,
    },
    {
        "name": "[DEMO] Everyday care introduction",
        "channels": ["LinkedIn", "Email"],
        "status": "draft",
        "assets": (
            ("care-linkedin", "LinkedIn", "[DEMO] Demo Botanicals lotion helps skin feel hydrated. Learn about everyday care."),
            ("care-email", "Email", "[DEMO] A simple daily routine can help skin feel hydrated."),
        ),
        "scan": False,
        "review": False,
    },
    {
        "name": "[DEMO] Member appreciation offer",
        "channels": ["Email", "Poster"],
        "status": "in_review",
        "assets": (
            ("member-email", "Email", "[DEMO] Enjoy 20% off selected moisturizers. Terms apply."),
            ("member-poster", "Poster", "[DEMO] Demo Botanicals: 20% off selected moisturizers. Terms apply."),
        ),
        "scan": True,
        "review": True,
    },
)


def _demo_user(db, account: dict[str, str]) -> User:
    normalized = account["email"].casefold()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    if user is None:
        user = User(
            email=account["email"],
            email_normalized=normalized,
            display_name=account["name"],
            password_hash=hash_password(account["password"]),
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
        db.flush()
    else:
        # These reserved public demo identities intentionally keep their displayed
        # credentials usable after container restarts. They are not real accounts.
        user.display_name = account["name"]
        user.password_hash = hash_password(account["password"])
        user.is_active = True
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    return user


def _ensure_membership(db, organization: Organization, user: User, role: str) -> None:
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == organization.id,
            Membership.user_id == user.id,
        )
    )
    if membership is None:
        db.add(Membership(organization_id=organization.id, user_id=user.id, role=role))
    else:
        membership.role = role


def _ensure_assets(db, organization: Organization, campaign: Campaign, creator: User, asset_specs) -> list[Asset]:
    assets: list[Asset] = []
    for group_id, channel, content in asset_specs:
        asset = db.scalar(
            select(Asset).where(
                Asset.organization_id == organization.id,
                Asset.campaign_id == campaign.id,
                Asset.asset_group_id == group_id,
                Asset.current.is_(True),
            )
        )
        if asset is None:
            asset = Asset(
                organization_id=organization.id,
                campaign_id=campaign.id,
                asset_type="text",
                channel=channel,
                language="en",
                asset_group_id=group_id,
                version=1,
                current=True,
                content_type="text/plain",
                sha256=sha256(content.encode("utf-8")).hexdigest(),
                size_bytes=len(content.encode("utf-8")),
                malware_status="not_applicable",
                extraction_status="complete",
                text_content=content,
                extracted_text=content,
                created_by=creator.id,
            )
            db.add(asset)
            db.flush()
        assets.append(asset)
    return assets


def seed_judge_demo() -> None:
    """Create/update public demo users and seed sample workflow data once."""
    with SessionLocal() as db:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext('brandlens-judge-demo-seed'))"))

        users = {account["role"]: _demo_user(db, account) for account in DEMO_ACCOUNTS}
        admin = users["admin"]
        creator = users["creator"]
        reviewer = users["reviewer"]

        organization = db.scalar(
            select(Organization).where(
                Organization.name == DEMO_ORGANIZATION,
                Organization.deleted_at.is_(None),
            )
        )
        if organization is None:
            organization = Organization(
                name=DEMO_ORGANIZATION,
                industry="Fictional consumer products",
                official_email="demo@example.com",
                website="https://brandlens.example.test",
                contact_person="Judge demo workspace",
                verification_status="approved",
                created_by=admin.id,
            )
            db.add(organization)
            db.flush()
        else:
            # Keep existing demo rows compatible with EmailStr response validation.
            organization.official_email = "demo@example.com"
        _ensure_membership(db, organization, admin, "admin")
        _ensure_membership(db, organization, creator, "creator")
        _ensure_membership(db, organization, reviewer, "reviewer")

        source = db.scalar(
            select(BrandGuidelineSource).where(
                BrandGuidelineSource.organization_id == organization.id,
                BrandGuidelineSource.title == "[DEMO] Demo Botanicals guidance",
                BrandGuidelineSource.deleted_at.is_(None),
            )
        )
        if source is None:
            combined_source = "\n\n".join(SOURCE_TEXTS)
            source = BrandGuidelineSource(
                organization_id=organization.id,
                title="[DEMO] Demo Botanicals guidance",
                document_ref="demo://judge-workspace/guidance.txt",
                original_filename="demo-guidance.txt",
                content_type="text/plain",
                sha256=sha256(combined_source.encode("utf-8")).hexdigest(),
                size_bytes=len(combined_source.encode("utf-8")),
                version=1,
                status="approved",
                effective_from=date.today() - timedelta(days=30),
                created_by=admin.id,
                approved_by=admin.id,
                approved_at=datetime.now(UTC),
            )
            db.add(source)
            db.flush()

        passages = []
        for index, passage_text in enumerate(SOURCE_TEXTS, start=1):
            passage = db.scalar(
                select(SourcePassage).where(
                    SourcePassage.organization_id == organization.id,
                    SourcePassage.source_id == source.id,
                    SourcePassage.text == passage_text,
                )
            )
            if passage is None:
                passage = SourcePassage(
                    organization_id=organization.id,
                    source_id=source.id,
                    text=passage_text,
                    page_number=index,
                    location_label=f"Demo guidance page {index}",
                )
                db.add(passage)
                db.flush()
            passages.append(passage)

        rule_specs = (
            ("discount_percent", {"percent": 20}, passages[1]),
            ("required_disclaimer", {"value": "Terms apply"}, passages[1]),
            ("banned_phrase", {"value": "cures eczema"}, passages[0]),
        )
        for rule_type, parameters, passage in rule_specs:
            rule = db.scalar(
                select(Rule).where(
                    Rule.organization_id == organization.id,
                    Rule.rule_type == rule_type,
                    Rule.status == "active",
                )
            )
            if rule is None:
                db.add(
                    Rule(
                        organization_id=organization.id,
                        rule_type=rule_type,
                        parameters=parameters,
                        source_passage_id=passage.id,
                        status="active",
                        created_by=admin.id,
                    )
                )

        db.flush()
        campaign_assets: dict[str, list[Asset]] = {}
        for campaign_spec in CAMPAIGNS:
            campaign = db.scalar(
                select(Campaign).where(
                    Campaign.organization_id == organization.id,
                    Campaign.name == campaign_spec["name"],
                    Campaign.deleted_at.is_(None),
                )
            )
            if campaign is None:
                today = date.today()
                campaign = Campaign(
                    organization_id=organization.id,
                    name=campaign_spec["name"],
                    channels=campaign_spec["channels"],
                    starts_at=today,
                    ends_at=today + timedelta(days=30),
                    language="en",
                    status=campaign_spec["status"],
                    created_by=creator.id,
                )
                db.add(campaign)
                db.flush()
            campaign_assets[campaign_spec["name"]] = _ensure_assets(
                db, organization, campaign, creator, campaign_spec["assets"]
            )

        db.commit()

        scan_ids = []
        for campaign_spec in CAMPAIGNS:
            if not campaign_spec["scan"]:
                continue
            campaign = db.scalar(
                select(Campaign).where(
                    Campaign.organization_id == organization.id,
                    Campaign.name == campaign_spec["name"],
                    Campaign.deleted_at.is_(None),
                )
            )
            existing_scan = db.scalar(
                select(Scan)
                .where(Scan.organization_id == organization.id, Scan.campaign_id == campaign.id)
                .order_by(Scan.created_at.desc())
            )
            if existing_scan is None:
                assets = campaign_assets[campaign_spec["name"]]
                scan = Scan(
                    organization_id=organization.id,
                    campaign_id=campaign.id,
                    status="queued",
                    asset_versions={asset.id: asset.version for asset in assets},
                    requested_by=creator.id,
                )
                db.add(scan)
                db.commit()
                scan_ids.append(scan.id)
            elif existing_scan.status == "queued":
                scan_ids.append(existing_scan.id)

    if scan_ids:
        from app.campaigns.scans import execute_campaign_scan

        for scan_id in scan_ids:
            execute_campaign_scan(organization.id, scan_id)

    with SessionLocal() as db:
        organization = db.scalar(
            select(Organization).where(Organization.name == DEMO_ORGANIZATION, Organization.deleted_at.is_(None))
        )
        reviewer = db.scalar(select(User).where(User.email_normalized == DEMO_ACCOUNTS[2]["email"]))
        creator = db.scalar(select(User).where(User.email_normalized == DEMO_ACCOUNTS[1]["email"]))
        review_campaign_spec = next(item for item in CAMPAIGNS if item["review"])
        campaign = db.scalar(
            select(Campaign).where(
                Campaign.organization_id == organization.id,
                Campaign.name == review_campaign_spec["name"],
            )
        )
        scan = db.scalar(
            select(Scan)
            .where(Scan.organization_id == organization.id, Scan.campaign_id == campaign.id, Scan.status == "completed")
            .order_by(Scan.created_at.desc())
        )
        if scan:
            existing_review = db.scalar(
                select(Review.id).where(Review.organization_id == organization.id, Review.scan_id == scan.id)
            )
            if existing_review is None:
                assets = db.scalars(
                    select(Asset).where(
                        Asset.organization_id == organization.id,
                        Asset.campaign_id == campaign.id,
                        Asset.current.is_(True),
                        Asset.deleted_at.is_(None),
                    )
                ).all()
                submission_id = str(uuid4())
                now = datetime.now(UTC)
                db.add_all(
                    [
                        Review(
                            organization_id=organization.id,
                            asset_id=asset.id,
                            asset_version=asset.version,
                            submission_id=submission_id,
                            submitted_by_user_id=creator.id,
                            scan_id=scan.id,
                            decision="pending",
                            comment="[DEMO] Review this sample campaign.",
                            created_at=now,
                        )
                        for asset in assets
                    ]
                )
                db.add(
                    AuditEvent(
                        organization_id=organization.id,
                        actor_user_id=creator.id,
                        action="campaign.submitted_for_review",
                        entity_type="campaign",
                        entity_id=campaign.id,
                        details={"demo_seed": True, "scan_id": scan.id, "submission_id": submission_id},
                    )
                )
                db.commit()


if __name__ == "__main__":
    seed_judge_demo()
