from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.campaigns.analytics import aggregate_analytics, compliance_score
from app.core.db import get_db
from app.db.models import Asset, AuditEvent, Campaign, Finding, Organization, Scan, User
from app.main import app


def test_compliance_score_weights_only_open_findings():
    findings = [
        SimpleNamespace(severity="high", status="open"),
        SimpleNamespace(severity="critical", status="resolved"),
    ]
    assert compliance_score(findings, 1) == 62
    assert compliance_score([], 0) == 100


def test_aggregate_empty_data_returns_complete_empty_payload():
    result = aggregate_analytics(scans=[], findings=[], assets=[], reviews=[], audit_events=[],
        start=date(2026, 1, 1), end=date(2026, 1, 2))
    assert result["summary"] == {"compliance_score": None, "open_findings": 0, "open_findings_percentage": 0,
        "average_review_minutes": None, "scans": 0, "completed_scans": 0, "findings": 0}
    assert result["violations"] == []
    assert result["campaigns"] == []
    assert len(result["trend"]) == 2


def test_aggregate_metrics_include_violation_share_repeat_and_turnaround():
    now = datetime.now(UTC)
    scan = SimpleNamespace(id="scan-1", campaign_id="campaign-1", status="completed", created_at=now - timedelta(hours=1))
    findings = [
        SimpleNamespace(id="f1", scan_id="scan-1", campaign_id="campaign-1", asset_id="asset-1", rule_id="rule-1", finding_type="discount_percent", severity="high", status="dismissed", created_at=now - timedelta(minutes=45)),
        SimpleNamespace(id="f2", scan_id="scan-1", campaign_id="campaign-1", asset_id="asset-1", rule_id="rule-1", finding_type="discount_percent", severity="medium", status="open", created_at=now),
        SimpleNamespace(id="f3", scan_id="scan-1", campaign_id="campaign-1", asset_id="asset-1", rule_id="rule-2", finding_type="unsupported_claim", severity="low", status="resolved", created_at=now),
    ]
    asset = SimpleNamespace(id="asset-1", campaign_id="campaign-1", campaign_name="Launch", channel="Instagram")
    events = [SimpleNamespace(action="finding.dismissed", entity_id="f1", created_at=now - timedelta(minutes=30)),
        SimpleNamespace(action="finding.resolved", entity_id="f3", created_at=now)]
    review = SimpleNamespace(scan_id="scan-1", decision="approved", created_at=now, reviewer_user_id="reviewer-1")
    result = aggregate_analytics(scans=[scan], findings=findings, assets=[asset], reviews=[review], audit_events=events,
        start=(now - timedelta(days=1)).date(), end=now.date())
    assert result["summary"]["findings"] == 3
    assert result["summary"]["open_findings"] == 1
    assert result["violations"][0]["percentage"] == 66.7
    assert result["review_times"]["median_minutes"] == 60
    assert result["confusing_rules"][0]["dismissal_rate"] == 50
    assert result["campaigns"][0]["campaign_name"] == "Launch"
    assert result["campaigns"][0]["scans"] == 1
    assert result["campaigns"][0]["average_turnaround_minutes"] == 50


def test_brand_health_endpoint_is_tenant_scoped_and_validates_filters(client):
    password = "Secure-password-456"
    client.post("/api/v1/auth/register", json={"email": "analytics-owner@example.com", "display_name": "Analytics Owner", "password": password})
    assert client.post("/api/v1/auth/login", json={"email": "analytics-owner@example.com", "password": password}).status_code == 200
    response = client.post("/api/v1/orgs", json={"name": "Analytics Workspace", "industry": "Retail", "official_email": "analytics@example.com", "website": "https://analytics.test", "contact_person": "Owner"})
    assert response.status_code == 201, response.text
    org_id = response.json()["id"]
    with next(app.dependency_overrides[get_db]()) as db:
        organization = db.get(Organization, org_id)
        organization.verification_status = "approved"
        owner = db.scalar(__import__("sqlalchemy").select(User).where(User.email_normalized == "analytics-owner@example.com"))
        campaign = Campaign(organization_id=org_id, name="Launch", channels=["Instagram"], starts_at=date.today(), ends_at=date.today(), language="en", status="draft", created_by=owner.id)
        db.add(campaign)
        db.flush()
        asset = Asset(organization_id=org_id, campaign_id=campaign.id, asset_type="text", channel="Instagram", language="en", current=True, content_type="text/plain", sha256="demo", size_bytes=10, malware_status="not_applicable", extraction_status="complete", text_content="Save 30%", extracted_text="Save 30%", created_by=owner.id)
        db.add(asset)
        db.flush()
        scan = Scan(organization_id=org_id, campaign_id=campaign.id, status="completed", requested_by=owner.id, created_at=datetime.now(UTC))
        db.add(scan)
        db.flush()
        db.add(Finding(organization_id=org_id, scan_id=scan.id, asset_id=asset.id, finding_type="discount_percent", severity="high", status="open", created_at=scan.created_at))
        db.commit()
        campaign_id = campaign.id

    url = f"/api/v1/orgs/{org_id}/analytics/brand-health"
    result = client.get(url)
    assert result.status_code == 200, result.text
    assert result.json()["summary"]["scans"] == 1
    assert result.json()["summary"]["open_findings"] == 1
    assert result.json()["campaigns"][0]["campaign_id"] == campaign_id
    assert client.get(url + f"?campaign_id={campaign_id}").json()["summary"]["scans"] == 1
    assert client.get(url + "?content_type=image").json()["summary"]["scans"] == 0
    assert client.get(url + "?severity=medium").json()["summary"]["findings"] == 0
    assert client.get(url + "?severity=urgent").status_code == 422
    assert client.get(url + "?start_date=2026-01-01&end_date=2024-01-01").status_code == 422
    assert client.get(f"/api/v1/orgs/not-a-member/analytics/brand-health").status_code == 404
