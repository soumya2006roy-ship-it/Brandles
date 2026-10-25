from urllib.parse import parse_qs, urlparse
from io import BytesIO

from docx import Document
import pymupdf
from sqlalchemy import select

from app.core.db import get_db
from app.core.security import digest_secret
from app.db.models import AuthToken, BrandGuidelineSource, Invite, Membership, Organization, PlatformAdmin, Rule, SessionRecord, SourcePassage, User
from app.main import app
from app.sources.documents import chunk_block, extract_document, identify_format, local_hash_embedding


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


def create_approved_organization(client, mailer, organization_email: str):
    owner_email = f"owner-{organization_email}"
    owner_password = register_user(client, mailer, email=owner_email)
    client.post("/api/v1/auth/login", json={"email": owner_email, "password": owner_password})
    organization = client.post("/api/v1/orgs", json={"name": "Verified Workspace", "industry": "Skincare", "official_email": organization_email, "website": "https://brand.test", "contact_person": "Brand Admin"}).json()
    client.post("/api/v1/auth/logout")
    platform_email = f"platform-{organization_email}"
    register_user(client, mailer, email=platform_email, display_name="Platform Operator")
    with next(app.dependency_overrides[get_db]()) as db:
        platform_user = db.scalar(select(User).where(User.email_normalized == platform_email))
        db.add(PlatformAdmin(user_id=platform_user.id))
        db.commit()
    client.post("/api/v1/auth/login", json={"email": platform_email, "password": "Secure-password-123"})
    approved = client.post(f"/api/v1/platform/verifications/{organization['id']}/decision", json={"decision": "approved"})
    assert approved.status_code == 200
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": owner_email, "password": owner_password})
    return organization, owner_email, owner_password


def test_sources_require_approval_and_preserve_versions_and_passage_provenance(client, mailer):
    organization, _, _ = create_approved_organization(client, mailer, "sources-brand@example.com")
    org_id = organization["id"]
    text = ("An approved source must support every exact brand claim. " * 80).encode()
    created = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Claims and offer terms"}, files={"document": ("claims.txt", text, "text/plain")})
    assert created.status_code == 201, created.text
    source = created.json()
    assert source["status"] == "draft"
    assert source["version"] == 1
    assert source["sha256"]
    detail = client.get(f"/api/v1/orgs/{org_id}/sources/{source['id']}").json()
    assert len(detail["passages"]) > 1
    assert detail["passages"][0]["page_number"] is None
    assert detail["passages"][0]["location_label"]

    passage_id = detail["passages"][0]["id"]
    blocked = client.post(f"/api/v1/orgs/{org_id}/rules", json={"rule_type": "banned_phrase", "parameters": {"value": "guaranteed cure"}, "source_passage_id": passage_id})
    assert blocked.status_code == 409
    approved = client.post(f"/api/v1/orgs/{org_id}/sources/{source['id']}/approve", json={"effective_from": "2026-10-01", "effective_to": "2027-10-01"})
    assert approved.status_code == 200
    download = client.get(f"/api/v1/orgs/{org_id}/sources/{source['id']}/download").json()
    private_path = download["url"].replace("/api/product/", "/api/v1/", 1)
    assert client.get(private_path).content == text
    rule = client.post(f"/api/v1/orgs/{org_id}/rules", json={"rule_type": "banned_phrase", "parameters": {"value": "guaranteed cure"}, "source_passage_id": passage_id})
    assert rule.status_code == 201, rule.text
    assert rule.json()["status"] == "active"

    next_version = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Claims and offer terms", "source_family_id": source["family_id"]}, files={"document": ("claims.md", b"The offer is now 25 percent off.", "text/markdown")})
    assert next_version.status_code == 201, next_version.text
    assert next_version.json()["version"] == 2
    approved_v2 = client.post(f"/api/v1/orgs/{org_id}/sources/{next_version.json()['id']}/approve", json={"effective_from": "2027-10-02", "effective_to": None})
    assert approved_v2.status_code == 200
    history = client.get(f"/api/v1/orgs/{org_id}/sources?family_id={source['family_id']}").json()
    assert [(row["version"], row["status"]) for row in history] == [(2, "approved"), (1, "archived")]
    with next(app.dependency_overrides[get_db]()) as db:
        saved_rule = db.scalar(select(Rule).where(Rule.id == rule.json()["id"]))
        assert saved_rule.status == "archived"
        old_source = db.scalar(select(BrandGuidelineSource).where(BrandGuidelineSource.id == source["id"]))
        assert len(db.scalars(select(SourcePassage).where(SourcePassage.source_id == old_source.id)).all()) > 0


def test_rule_suggestions_are_not_active_until_admin_approval_and_upload_checks_magic_bytes(client, mailer):
    organization, owner_email, owner_password = create_approved_organization(client, mailer, "rules-brand@example.com")
    org_id = organization["id"]
    bad_upload = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Misleading extension"}, files={"document": ("fake.pdf", b"just a text file", "application/pdf")})
    assert bad_upload.status_code == 415
    upload = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Approved offer"}, files={"document": ("offer.md", b"Offer name: Winter Glow. Discount: 20 percent.", "text/markdown")}).json()
    detail = client.get(f"/api/v1/orgs/{org_id}/sources/{upload['id']}").json()
    client.post(f"/api/v1/orgs/{org_id}/sources/{upload['id']}/approve", json={"effective_from": "2026-01-01"})
    client.post("/api/v1/auth/logout")

    creator_email = "rule-creator@example.com"
    register_user(client, mailer, email=creator_email, display_name="Rule Creator")
    with next(app.dependency_overrides[get_db]()) as db:
        creator = db.scalar(select(User).where(User.email_normalized == creator_email))
        db.add(Membership(organization_id=org_id, user_id=creator.id, role="creator"))
        db.commit()
    client.post("/api/v1/auth/login", json={"email": creator_email, "password": "Secure-password-123"})
    suggested = client.post(f"/api/v1/orgs/{org_id}/rules", json={"rule_type": "discount_percent", "parameters": {"percent": 20}, "source_passage_id": detail["passages"][0]["id"]})
    assert suggested.status_code == 201, suggested.text
    assert suggested.json()["status"] == "suggested"
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": owner_email, "password": owner_password})
    decision = client.post(f"/api/v1/orgs/{org_id}/rules/{suggested.json()['id']}/decision", json={"decision": "approve"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "active"


def test_document_parser_handles_pdf_docx_text_and_produces_deterministic_vectors():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Approved statement for page referenced evidence.")
    pdf_bytes = pdf.tobytes()
    assert identify_format("guide.pdf", pdf_bytes)[0] == "pdf"
    pdf_blocks = extract_document("pdf", pdf_bytes)
    assert pdf_blocks[0].page_number == 1
    assert "Approved statement" in pdf_blocks[0].text

    word = Document()
    word.add_paragraph("Approved DOCX statement for campaign sources.")
    docx_buffer = BytesIO()
    word.save(docx_buffer)
    docx_bytes = docx_buffer.getvalue()
    assert identify_format("guide.docx", docx_bytes)[0] == "docx"
    docx_blocks = extract_document("docx", docx_bytes)
    assert docx_blocks[0].page_number is None
    assert "Paragraphs" in (docx_blocks[0].location_label or "")

    text_bytes = "A long passage for overlap chunking. " .encode() * 150
    text_blocks = extract_document("guide.txt", text_bytes)
    chunks = chunk_block(text_blocks[0])
    assert len(chunks) > 1
    assert chunks[0][1] == 0
    assert chunks[1][1] < chunks[0][2]
    assert local_hash_embedding(chunks[0][0]) == local_hash_embedding(chunks[0][0])
    assert len(local_hash_embedding(chunks[0][0])) == 1536


