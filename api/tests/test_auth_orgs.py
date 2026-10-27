from urllib.parse import parse_qs, urlparse
from io import BytesIO

from docx import Document
import pymupdf
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.db import get_db
from app.core.security import digest_secret, hash_password
from app.db.models import Asset, AuditEvent, BrandGuidelineSource, Campaign, Finding, Invite, Membership, Organization, PlatformAdmin, Rule, Scan, SessionRecord, SourcePassage, User
from app.main import app
from app.sources.documents import chunk_block, extract_document, identify_format, local_hash_embedding
from app.campaigns import router as campaigns_router, scans as campaign_scans
from app.campaigns.scans import execute_campaign_scan


def register_user(client, mailer, *, email: str, display_name: str = "Test Person", password: str = "Secure-password-123"):
    response = client.post("/api/v1/auth/register", json={"email": email, "display_name": display_name, "password": password})
    assert response.status_code == 201
    assert response.json()["message"] == "Your account is ready. Sign in to continue."
    assert not any("Verify your BrandLens account" in message.subject for message in mailer.sent)
    return password


def test_registration_needs_no_email_verification_and_password_reset_is_single_use(client, mailer):
    password = register_user(client, mailer, email="creator@example.com")
    with next(app.dependency_overrides[get_db]()) as db:
        user = db.scalar(select(User).where(User.email_normalized == "creator@example.com"))
        assert user.email_verified_at is None
    assert client.get("/api/v1/auth/verify-email?token=unused").status_code == 404
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


def test_local_bootstrap_admin_email_can_sign_in(client):
    password = "Local-admin-password-456"
    with next(app.dependency_overrides[get_db]()) as db:
        user = User(email="admin@brandlens.local", email_normalized="admin@brandlens.local", display_name="Local Admin", password_hash=hash_password(password))
        db.add(user)
        db.commit()

    login = client.post("/api/v1/auth/login", json={"email": "admin@brandlens.local", "password": password})
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "admin@brandlens.local"
    assert client.get("/api/v1/auth/me").json()["email"] == "admin@brandlens.local"


def test_pending_organisation_cannot_issue_invites_until_platform_approval(client, mailer):
    password = register_user(client, mailer, email="owner@example.com")
    client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": password})
    created = client.post("/api/v1/orgs", json={"name": "Acme Skincare", "industry": "Skincare", "official_email": "brand@example.com", "website": "https://example.test", "contact_person": "Owner Person"})
    assert created.status_code == 201
    organization = created.json()
    assert organization["verification_status"] == "pending_verification"
    org_id = organization["id"]
    assert client.post(f"/api/v1/orgs/{org_id}/invites", json={"role": "reviewer"}).status_code == 423

    # Even an otherwise trusted operator cannot verify an organisation they submitted.
    with next(app.dependency_overrides[get_db]()) as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@example.com"))
        db.add(PlatformAdmin(user_id=owner.id))
        db.commit()
    assert client.post(f"/api/v1/platform/verifications/{org_id}/decision", json={"decision": "approved"}).status_code == 403

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


def test_expired_invite_is_rejected(client, mailer):
    organization, _owner_email, _owner_password = create_approved_organization(client, mailer, "expired-invite@example.com")
    org_id = organization["id"]
    invite = client.post(f"/api/v1/orgs/{org_id}/invites", json={"role": "creator", "expires_in_days": 1})
    assert invite.status_code == 201, invite.text
    code = invite.json()["code"]
    with next(app.dependency_overrides[get_db]()) as db:
        stored = db.scalar(select(Invite).where(Invite.organization_id == org_id))
        stored.expires_at = stored.expires_at.replace(year=2000)
        db.commit()
    register_user(client, mailer, email="expired-invite-member@example.com")
    client.post("/api/v1/auth/login", json={"email": "expired-invite-member@example.com", "password": "Secure-password-123"})
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


def test_campaign_assets_validate_content_strip_image_metadata_match_approved_logo_and_stale_prior_scans(client, mailer):
    organization, owner_email, owner_password = create_approved_organization(client, mailer, "campaign-brand@example.com")
    org_id = organization["id"]
    campaign_result = client.post(f"/api/v1/orgs/{org_id}/campaigns", json={"name": "Winter Glow Launch", "channels": ["Instagram caption", "Poster"], "starts_at": "2026-11-01", "ends_at": "2026-12-15", "language": "en"})
    assert campaign_result.status_code == 201, campaign_result.text
    campaign_id = campaign_result.json()["id"]

    text_asset_result = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Instagram caption", "text_content": "Winter Glow is here. Save 20 percent this season."})
    assert text_asset_result.status_code == 201, text_asset_result.text
    text_asset = text_asset_result.json()
    assert text_asset["asset_type"] == "text"
    assert text_asset["current"] is True

    with next(app.dependency_overrides[get_db]()) as db:
        owner = db.scalar(select(User).where(User.email_normalized == owner_email))
        scan = Scan(organization_id=org_id, campaign_id=campaign_id, asset_id=text_asset["id"], status="complete", requested_by=owner.id)
        db.add(scan)
        db.flush()
        finding = Finding(organization_id=org_id, scan_id=scan.id, asset_id=text_asset["id"], finding_type="offer_claim", severity="warning", quoted_excerpt="20 percent", confidence=0.8)
        db.add(finding)
        db.commit()
        scan_id, finding_id = scan.id, finding.id

    replacement = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Instagram caption", "asset_group_id": text_asset["asset_group_id"], "text_content": "Winter Glow now saves 25 percent."})
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["version"] == 2
    assert replacement.json()["supersedes_asset_id"] == text_asset["id"]
    with next(app.dependency_overrides[get_db]()) as db:
        assert db.get(Scan, scan_id).status == "stale"
        assert db.get(Finding, finding_id).status == "stale"

    logo = Image.new("RGB", (96, 72), (218, 154, 88))
    exif = Image.Exif(); exif[271] = "Metadata should be removed"
    logo_bytes = BytesIO(); logo.save(logo_bytes, format="PNG", exif=exif)
    png = logo_bytes.getvalue()
    logo_source_result = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Approved winter logo"}, files={"document": ("logo.png", png, "image/png")})
    assert logo_source_result.status_code == 201, logo_source_result.text
    logo_source = logo_source_result.json()
    passage = client.get(f"/api/v1/orgs/{org_id}/sources/{logo_source['id']}").json()["passages"][0]
    assert client.post(f"/api/v1/orgs/{org_id}/sources/{logo_source['id']}/approve", json={"effective_from": "2026-01-01"}).status_code == 200
    logo_rule = client.post(f"/api/v1/orgs/{org_id}/rules", json={"rule_type": "approved_logo", "parameters": {"version": "winter-logo-v1"}, "source_passage_id": passage["id"]})
    assert logo_rule.status_code == 201, logo_rule.text

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": owner_email, "password": owner_password})
    poster = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Poster"}, files={"file": ("misleading.txt", png, "text/plain")})
    assert poster.status_code == 201, poster.text
    poster_asset = poster.json()
    assert poster_asset["asset_type"] == "image"
    assert poster_asset["content_type"] == "image/png"
    assert poster_asset["metadata_stripped"] is True
    assert poster_asset["logo_matches"][0]["matched"] is True

    text_claimed_as_pdf = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Poster"}, files={"file": ("fake.pdf", b"plain text is not a PDF", "application/pdf")})
    assert text_claimed_as_pdf.status_code == 201
    assert text_claimed_as_pdf.json()["asset_type"] == "document"
    assert text_claimed_as_pdf.json()["content_type"] == "text/markdown"
    malformed_pdf = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Poster"}, files={"file": ("broken.pdf", b"%PDF- this is not a valid document", "application/pdf")})
    assert malformed_pdf.status_code == 422


def test_campaign_review_submission_is_idempotent_and_version_bound(client, mailer, monkeypatch):
    organization, _owner_email, _owner_password = create_approved_organization(client, mailer, "review-team@example.com")
    org_id = organization["id"]
    campaign_response = client.post(f"/api/v1/orgs/{org_id}/campaigns", json={"name": "Reviewable campaign", "channels": ["Instagram"], "language": "en"})
    assert campaign_response.status_code == 201
    campaign_id = campaign_response.json()["id"]
    asset_response = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets", data={"channel": "Instagram", "text_content": "A short caption for review."})
    assert asset_response.status_code == 201
    monkeypatch.setattr(campaigns_router, "enqueue", lambda *_args, **_kwargs: None)
    scan_response = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans")
    assert scan_response.status_code == 202
    scan_id = scan_response.json()["id"]
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    factory = sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False)
    db_generator.close()
    monkeypatch.setattr(campaign_scans, "SessionLocal", factory)
    execute_campaign_scan(org_id, scan_id)
    submission = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/submit", json={"scan_id": scan_id})
    assert submission.status_code == 202, submission.text
    submission_id = submission.json()[0]["submission_id"]
    duplicate = client.post(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}/submit", json={"scan_id": scan_id})
    assert duplicate.status_code == 202
    assert duplicate.json()[0]["submission_id"] == submission_id

    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner-review-team@example.com"))
        membership = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == owner.id))
        membership.role = "reviewer"
        db.commit()
    self_decision = client.post(f"/api/v1/orgs/{org_id}/reviews/{submission_id}/decision", json={"decision": "approve"})
    assert self_decision.status_code == 403
    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner-review-team@example.com"))
        membership = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == owner.id))
        membership.role = "admin"
        db.commit()

    client.post("/api/v1/auth/logout")
    register_user(client, mailer, email="campaign-reviewer@example.com", display_name="Campaign Reviewer")
    with factory() as db:
        reviewer = db.scalar(select(User).where(User.email_normalized == "campaign-reviewer@example.com"))
        db.add(Membership(organization_id=org_id, user_id=reviewer.id, role="reviewer"))
        db.commit()
    client.post("/api/v1/auth/login", json={"email": "campaign-reviewer@example.com", "password": "Secure-password-123"})
    queue = client.get(f"/api/v1/orgs/{org_id}/reviews/queue")
    assert queue.status_code == 200
    assert queue.json()[0]["submission_id"] == submission_id
    decision = client.post(f"/api/v1/orgs/{org_id}/reviews/{submission_id}/decision", json={"decision": "approve"})
    assert decision.status_code == 200
    assert decision.json()[0]["decision"] == "approved"
    duplicate_decision = client.post(f"/api/v1/orgs/{org_id}/reviews/{submission_id}/decision", json={"decision": "approve"})
    assert duplicate_decision.status_code == 200
    assert client.get(f"/api/v1/orgs/{org_id}/reviews/queue").json() == []
    assert client.get(f"/api/v1/orgs/{org_id}/campaigns/{campaign_id}").json()["status"] == "approved"
    with factory() as db:
        actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.organization_id == org_id)).all())
        assert {"campaign.submitted_for_review", "campaign.review_approved"}.issubset(actions)


def test_brand_twin_cites_only_approved_evidence_and_refuses_gaps(client, mailer):
    organization, _email, _password = create_approved_organization(client, mailer, "brand-twin@example.com")
    org_id = organization["id"]
    refused = client.post(f"/api/v1/orgs/{org_id}/brand-twin/ask", json={"question": "What does the brand say about moon dust?"})
    assert refused.status_code == 200
    assert refused.json()["insufficient_evidence"] is True
    assert refused.json()["citations"] == []

    source_response = client.post(f"/api/v1/orgs/{org_id}/sources", data={"title": "Offer reference"}, files={"document": ("offer.txt", b"The approved offer is 20% off until June 30.", "text/plain")})
    assert source_response.status_code == 201, source_response.text
    source_id = source_response.json()["id"]
    assert client.post(f"/api/v1/orgs/{org_id}/sources/{source_id}/approve", json={"effective_from": "2020-01-01"}).status_code == 200
    answer = client.post(f"/api/v1/orgs/{org_id}/brand-twin/ask", json={"question": "What is the approved offer?"})
    assert answer.status_code == 200
    assert answer.json()["insufficient_evidence"] is False
    assert answer.json()["citations"][0]["source_id"] == source_id
    assert answer.json()["citations"][0]["source_version"] == 1
