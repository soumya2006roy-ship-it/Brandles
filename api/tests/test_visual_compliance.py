from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw
from sqlalchemy import select

from app.assets.visual import confidence_outcome, delta_e_2000, dominant_palette, normalize_bbox, visual_findings
from app.core.db import get_db
from app.db.models import Organization
from app.main import app
from app.campaigns import router as campaigns_router


def image_bytes(color: str = "#b04030", size: tuple[int, int] = (240, 160)) -> bytes:
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 80, 58), fill="#213f30")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_delta_e_2000_and_palette_are_deterministic():
    assert delta_e_2000("#FFFFFF", "#FFFFFF") == 0
    assert delta_e_2000("#000000", "#FFFFFF") > 90
    assert dominant_palette(image_bytes())[0]["hex"] == "#b04030"


def test_bbox_is_normalized_and_confidence_is_bounded():
    assert normalize_bbox((25, 20, 75, 60), 100, 80) == {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5}
    assert confidence_outcome(1.8, 0.7) == {"confidence": 1.0, "needs_human_review": False}
    assert confidence_outcome(0.2, 0.7)["needs_human_review"] is True


def test_visual_colour_check_has_source_and_review_state():
    rule = SimpleNamespace(id="colour-rule", parameters={"colors": ["#163d2b"], "tolerance_delta_e": 10})
    passage = SimpleNamespace(id="colour-passage", text="Use forest green for the poster background.")
    result = visual_findings(image_bytes=image_bytes(), color_rules=[(rule, passage)], logo_matches=[], disclaimer_rules=[], ocr_text=None)
    finding = next(item for item in result["findings"] if item["finding_type"] == "brand_color_deviation")
    assert finding["source_passage_id"] == "colour-passage"
    assert finding["bounding_box"] == {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    assert finding["confidence"] <= 1
    assert result["palette"]["status"] == "review"


def test_visual_logo_and_disclaimer_prototype_behaviour():
    logo = {"matched": True, "deprecated": True, "similarity": 0.95, "logo_version": "retired-v1", "rule_id": "logo-rule", "passage_id": "logo-passage", "quoted_excerpt": "Retired logo"}
    disclaimer_rule = SimpleNamespace(id="disclaimer-rule", parameters={"value": "Terms apply"})
    disclaimer_passage = SimpleNamespace(id="terms-passage", text="Always include: Terms apply.")
    without_ocr = visual_findings(image_bytes=image_bytes(), color_rules=[], logo_matches=[logo], disclaimer_rules=[(disclaimer_rule, disclaimer_passage)], ocr_text=None)
    assert without_ocr["logo"]["status"] == "deprecated"
    assert without_ocr["disclaimer"]["status"] == "not_verifiable"
    with_ocr = visual_findings(image_bytes=image_bytes(), color_rules=[], logo_matches=[], disclaimer_rules=[(disclaimer_rule, disclaimer_passage)], ocr_text="Summer offer")
    missing = next(item for item in with_ocr["findings"] if item["finding_type"] == "missing_disclaimer")
    assert missing["source_passage_id"] == "terms-passage"
    assert missing["bounding_box"] is None


def test_generated_visual_fixture_set_covers_expected_cases():
    fixture_dir = Path(__file__).parent / "fixtures" / "visual"
    expected = {"compliant-poster.png", "wrong-logo.png", "off-brand-colours.png", "missing-disclaimer.png", "blurry-low-quality.png"}
    assert expected.issubset({path.name for path in fixture_dir.glob("*.png")})
    for name in expected:
        assert Image.open(fixture_dir / name).size == (720, 480)


def test_visual_check_upload_validates_content_and_queues_existing_scan(client, mailer, monkeypatch):
    email = "visual-owner@example.com"
    password = "Secure-password-456"
    assert client.post("/api/v1/auth/register", json={"email": email, "display_name": "Visual Owner", "password": password}).status_code == 201
    assert client.post("/api/v1/auth/login", json={"email": email, "password": password}).status_code == 200
    organization = client.post("/api/v1/orgs", json={"name": "Visual Workspace", "industry": "Retail", "official_email": "visual-team@example.com", "website": "https://visual.test", "contact_person": "Visual Owner"}).json()
    org_id = organization["id"]
    with next(app.dependency_overrides[get_db]()) as db:
        db.scalar(select(Organization).where(Organization.id == org_id)).verification_status = "approved"
        db.commit()
    campaign = client.post(f"/api/v1/orgs/{org_id}/campaigns", json={"name": "Visual launch", "channels": ["Poster"], "language": "en"}).json()
    monkeypatch.setattr(campaigns_router, "enqueue", lambda *_args, **_kwargs: None)
    endpoint = f"/api/v1/orgs/{org_id}/campaigns/{campaign['id']}/visual-check"
    fixture = Path(__file__).parent / "fixtures" / "visual" / "compliant-poster.png"
    contents = fixture.read_bytes()

    wrong_type = client.post(endpoint, data={"channel": "Poster"}, files={"file": ("renamed.png", b"plain text renamed to png", "image/png")})
    assert wrong_type.status_code == 415
    corrupt = client.post(endpoint, data={"channel": "Poster"}, files={"file": ("broken.png", b"\\x89PNG\\r\\nnot an image", "image/png")})
    assert corrupt.status_code == 415

    monkeypatch.setattr(campaigns_router, "MAX_ASSET_BYTES", 100)
    too_large = client.post(endpoint, data={"channel": "Poster"}, files={"file": ("large.png", contents, "image/png")})
    assert too_large.status_code == 413
    monkeypatch.setattr(campaigns_router, "MAX_ASSET_BYTES", 25 * 1024 * 1024)

    queued = client.post(endpoint, data={"channel": "Poster"}, files={"file": ("poster.png", contents, "image/png")})
    assert queued.status_code == 202, queued.text
    assert queued.json()["asset"]["asset_type"] == "image"
    assert queued.json()["scan"]["status"] == "queued"
