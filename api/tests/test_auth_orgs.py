from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.core.db import get_db
from app.core.security import digest_secret
from app.db.models import AuthToken, Invite, Membership, Organization, PlatformAdmin, SessionRecord, User
from app.main import app


def register_user(client, mailer, *, email: str, display_name: str = "Test Person", password: str = "Secure-password-123"):
    response = client.post("/api/v1/auth/register", json={"email": email, "display_name": display_name, "password": password})
    assert response.status_code == 202
    verification_url = mailer.sent[-1].text.splitlines()[2]
    token = parse_qs(urlparse(verification_url).query)["token"][0]
    verification = client.get(f"/api/v1/auth/verify-email?token={token}")
    assert verification.status_code == 200
    assert client.get(f"/api/v1/auth/verify-email?token={token}").status_code == 400
    return password


def test_email_verification_sessions_and_password_reset_are_single_use(client, mailer):
    password = register_user(client, mailer, email="creator@example.com")
    login = client.post("/api/v1/auth/login", json={"email": "creator@example.com", "password": password})
    assert login.status_code == 200
    cookie = login.cookies.get("brandlens_session")
    assert cookie
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").json()["email"] == "creator@example.com"
    assert len(client.get("/api/v1/auth/sessions").json()) == 1

    client.post("/api/v1/auth/password-reset", json={"email": "missing@example.com"})
    reset_request = client.post("/api/v1/auth/password-reset", json={"email": "creator@example.com"})
    assert reset_request.status_code == 202
    reset_url = mailer.sent[-1].text.splitlines()[0].split(": ", maxsplit=1)[-1]
    reset_token = parse_qs(urlparse(reset_url).query)["token"][0]
    reset = client.post("/api/v1/auth/password-reset/confirm", json={"token": reset_token, "password": "New-password-456"})
    assert reset.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/password-reset/confirm", json={"token": reset_token, "password": "Other-password-789"}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "creator@example.com", "password": "New-password-456"}).status_code == 200


def test_pending_organisation_cannot_issue_invites_until_platform_approval(client, mailer):
    password = register_user(client, mailer, email="owner@example.com")
    client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": password})
    created = client.post("/api/v1/orgs", json={"name": "Acme Skincare", "industry": "Skincare", "official_email": "brand@example.com", "website": "https://example.test", "contact_person": "Owner Person"})
    assert created.status_code == 201
    organization = created.json()
    assert organization["verification_status"] == "pending_verification"
    org_id = organization["id"]
    assert client.post(f"/api/v1/orgs/{org_id}/invites", json={"role": "reviewer"}).status_code == 423

    register_user(client, mailer, email="platform@example.com", display_name="Platform Admin")
    client.post("/api/v1/auth/logout")
    with next(app.dependency_overrides[get_db]()) as db:
        platform_user = db.scalar(select(User).where(User.email_normalized == "platform@example.com"))
        db.add(PlatformAdmin(user_id=platform_user.id))
        db.commit()
    admin_login = client.post("/api/v1/auth/login", json={"email": "platform@example.com", "password": "Secure-password-123"})
    assert admin_login.status_code == 200
    decision = client.post(f"/api/v1/platform/verifications/{org_id}/decision", json={"decision": "approved"})
    assert decision.status_code == 200
    assert decision.json()["verification_status"] == "approved"
    history = client.get(f"/api/v1/platform/verifications/{org_id}/history")
    assert history.status_code == 200
    assert history.json()[0]["decision"] == "approved"

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": password})
    invite_response = client.post(f"/api/v1/orgs/{org_id}/invites", json={"role": "reviewer", "usage_limit": 1})
    assert invite_response.status_code == 201
    code = invite_response.json()["code"]
    with next(app.dependency_overrides[get_db]()) as db:
        stored = db.scalar(select(Invite).where(Invite.organization_id == org_id))
        assert stored.code_hash == digest_secret(code)
        assert stored.code_hash != code

    register_user(client, mailer, email="reviewer@example.com", display_name="Reviewer Person")
    client.post("/api/v1/auth/login", json={"email": "reviewer@example.com", "password": "Secure-password-123"})
    joined = client.post("/api/v1/invites/redeem", json={"code": code})
    assert joined.status_code == 201
    assert joined.json()["role"] == "reviewer"
    assert client.post("/api/v1/invites/redeem", json={"code": code}).status_code == 400


def test_invites_are_tenant_scoped_and_roles_are_enforced(client, mailer):
    owner_password = register_user(client, mailer, email="tenant-admin@example.com")
    client.post("/api/v1/auth/login", json={"email": "tenant-admin@example.com", "password": owner_password})
    organization = client.post("/api/v1/orgs", json={"name": "First Org", "industry": "Retail", "official_email": "team@first.com", "website": "https://first.test", "contact_person": "First Admin"}).json()
    org_id = organization["id"]
    client.post("/api/v1/auth/logout")
    register_user(client, mailer, email="outsider@example.com", display_name="Outside User")
    client.post("/api/v1/auth/login", json={"email": "outsider@example.com", "password": "Secure-password-123"})
    assert client.get(f"/api/v1/orgs/{org_id}").status_code == 404
    assert client.post(f"/api/v1/orgs/{org_id}/invites", json={"role": "creator"}).status_code == 404


