from datetime import date, timedelta

from sqlalchemy import select

from app.campaigns.health import evaluate_campaign_health
from app.core.db import get_db
from app.core.security import hash_password
from app.db.models import Campaign, Membership, Organization, PlatformAdmin, User
from app.main import app


def _evaluate(**overrides):
    values = {
        "starts_at": date.today() - timedelta(days=1),
        "ends_at": date.today() + timedelta(days=5),
        "today": date.today(),
        "channels": ["Instagram", "Email"],
        "asset_channels": ["Instagram", "Email"],
        "scan_status": "completed",
        "scan_is_current": True,
        "open_severities": [],
        "days_since_update": 0,
    }
    values.update(overrides)
    return evaluate_campaign_health(**values)


def test_health_scenarios_have_expected_status_and_score():
    assert _evaluate() == {
        "score": 100,
        "status": "healthy",
        "checks": [
            {"key": "date_window", "status": "pass", "detail": "The campaign is within its configured date window.", "recommendation": ""},
            {"key": "assets", "status": "pass", "detail": "Current assets cover all 2 selected channel(s).", "recommendation": ""},
            {"key": "scan", "status": "pass", "detail": "A completed scan matches the current assets and rules.", "recommendation": ""},
            {"key": "findings", "status": "pass", "detail": "No open High or Critical findings were found on the latest scan.", "recommendation": ""},
            {"key": "freshness", "status": "pass", "detail": "Campaign activity is within the freshness window.", "recommendation": ""},
        ],
        "recommendations": [],
    }
    assert _evaluate(ends_at=date.today() - timedelta(days=1))["status"] == "critical"
    assert _evaluate(asset_channels=["Instagram"])["status"] == "warning"
    assert _evaluate(scan_status="completed", scan_is_current=False)["status"] == "warning"
    assert _evaluate(open_severities=["high"])["status"] == "warning"
    assert _evaluate(open_severities=["critical"])["status"] == "critical"
    assert _evaluate(starts_at=None, ends_at=None, asset_channels=[], scan_status=None, scan_is_current=False)["status"] == "warning"


def test_campaign_health_endpoints_are_organisation_scoped(client, mailer):
    password = "Secure-password-456"
    client.post("/api/v1/auth/register", json={"email": "health-owner@example.com", "display_name": "Health Owner", "password": password, "recovery_question": "first_pet", "recovery_answer": "Milo"})
    assert client.post("/api/v1/auth/login", json={"email": "health-owner@example.com", "password": password}).status_code == 200
    response = client.post("/api/v1/orgs", json={"name": "Health Workspace", "industry": "Retail", "official_email": "health@example.com", "website": "https://example.test", "contact_person": "Health Owner"})
    assert response.status_code == 201, response.text
    org_id = response.json()["id"]
    with next(app.dependency_overrides[get_db]()) as db:
        organization = db.get(Organization, org_id)
        organization.verification_status = "approved"
        db.commit()
    created = client.post(f"/api/v1/orgs/{org_id}/campaigns", json={"name": "Spring launch", "channels": ["Instagram"], "starts_at": date.today().isoformat(), "ends_at": (date.today() + timedelta(days=5)).isoformat(), "language": "en"})
    assert created.status_code == 201, created.text
    overview = client.get(f"/api/v1/orgs/{org_id}/campaigns/health", headers={"accept-language": "hi"})
    assert overview.status_code == 200, overview.text
    assert overview.json()["warning_count"] == 1
    assert any("अभियान" in check["detail"] for check in overview.json()["campaigns"][0]["checks"])
    campaign_id = created.json()["id"]

    with next(app.dependency_overrides[get_db]()) as db:
        other = User(email="other-health@example.com", email_normalized="other-health@example.com", display_name="Other", password_hash=hash_password(password))
        db.add(other)
        db.flush()
        foreign_org = Organization(name="Other Workspace", industry="Retail", official_email="other@example.com", website="https://other.test", contact_person="Other", verification_status="approved", created_by=other.id)
        db.add(foreign_org)
        db.flush()
        db.add(Membership(organization_id=foreign_org.id, user_id=other.id, role="admin"))
        foreign_campaign = Campaign(organization_id=foreign_org.id, name="Private campaign", channels=["Email"], starts_at=date.today(), ends_at=date.today(), language="en", status="draft", created_by=other.id)
        db.add(foreign_campaign)
        db.commit()
        foreign_org_id, foreign_campaign_id = foreign_org.id, foreign_campaign.id

    assert client.get(f"/api/v1/orgs/{foreign_org_id}/campaigns/health").status_code == 404
    assert client.get(f"/api/v1/orgs/{org_id}/campaigns/{foreign_campaign_id}/health").status_code == 404
    assert client.get(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/health").status_code == 200
    with next(app.dependency_overrides[get_db]()) as db:
        owner = db.scalar(select(User).where(User.email_normalized == "health-owner@example.com"))
        db.add(PlatformAdmin(user_id=owner.id))
        db.commit()
    assert client.get(f"/api/v1/orgs/{foreign_org_id}/campaigns/health").status_code == 200
