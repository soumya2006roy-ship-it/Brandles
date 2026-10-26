"""Run the labelled BrandLens scan examples against the deterministic engine."""

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import Base
from app.db.models import Asset, BrandGuidelineSource, Campaign, Finding, Rule, Scan, SourcePassage, User
from app.campaigns import scans


class EvaluationLLMClient:
    """Deterministic test fixture: judgement is always insufficient evidence."""

    vendor = "evaluation-fixture"
    model = "insufficient-evidence-v1"

    def judge(self, task, approved_passages, asset_excerpt):
        del task, approved_passages, asset_excerpt
        return {"verdict": "insufficient_evidence", "flagged_text": None, "source_id": None, "quoted_excerpt": None, "rationale": "No model judgement is configured in this evaluation.", "confidence": 0.0, "suggested_fix": None}


def main() -> int:
    examples = json.loads((ROOT / "evals" / "brandlens.json").read_text(encoding="utf-8"))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    scans.SessionLocal = factory
    scans.get_llm_client = lambda _organization: EvaluationLLMClient()
    expected_total = predicted_total = correct = 0
    high_false_breaches = possible_false_breaches = 0
    valid_citations = citations = 0
    try:
        for index, example in enumerate(examples):
            with factory() as db:
                user = User(email=f"eval-{index}@example.test", email_normalized=f"eval-{index}@example.test", display_name="Eval", password_hash="test", email_verified_at=datetime.now(UTC))
                db.add(user)
                db.flush()
                from app.db.models import Organization
                org = Organization(name=example["name"], industry="Evaluation", official_email=user.email, website="https://example.test", contact_person="Eval", verification_status="approved", llm_processing_allowed=True, created_by=user.id)
                db.add(org)
                db.flush()
                campaign = Campaign(organization_id=org.id, name=example["name"], channels=[asset["channel"] for asset in example["assets"]], starts_at=date.today(), ends_at=date.today(), language="en", status="draft", created_by=user.id)
                db.add(campaign)
                source = BrandGuidelineSource(organization_id=org.id, title="Evaluation source", document_ref="private/eval.txt", original_filename="eval.txt", content_type="text/plain", sha256="eval", size_bytes=len(example["approved_passage"]), version=1, status="approved", effective_from=date.today(), created_by=user.id, approved_by=user.id, approved_at=datetime.now(UTC))
                db.add(source)
                db.flush()
                passage = SourcePassage(organization_id=org.id, source_id=source.id, text=example["approved_passage"], page_number=1)
                db.add(passage)
                db.flush()
                rule_spec = example.get("rule")
                if rule_spec:
                    db.add(Rule(organization_id=org.id, rule_type=rule_spec["type"], parameters=rule_spec["parameters"], source_passage_id=passage.id, status="active", created_by=user.id))
                for asset_index, item in enumerate(example["assets"]):
                    text = item["text"]
                    db.add(Asset(organization_id=org.id, campaign_id=campaign.id, asset_type="text", channel=item["channel"], language="en", asset_group_id=f"asset-{asset_index}", version=1, current=True, content_type="text/plain", sha256=str(asset_index), size_bytes=len(text), malware_status="not_applicable", extraction_status="complete", text_content=text, extracted_text=text, created_by=user.id))
                db.flush()
                scan = Scan(organization_id=org.id, campaign_id=campaign.id, status="queued", requested_by=user.id)
                db.add(scan)
                db.commit()
                org_id, scan_id = org.id, scan.id
            scans.execute_campaign_scan(org_id, scan_id)
            with factory() as db:
                rows = db.scalars(select(Finding).where(Finding.organization_id == org_id, Finding.scan_id == scan_id)).all()
                expected = set(example["expected_types"])
                predicted = {row.finding_type for row in rows}
                expected_total += len(expected)
                predicted_total += len(predicted)
                correct += len(expected & predicted)
                if not example["expect_high_finding"]:
                    possible_false_breaches += 1
                    high_false_breaches += sum(1 for row in rows if row.severity in {"high", "critical"})
                for row in rows:
                    if row.source_passage_id:
                        citations += 1
                        passage_row = db.scalar(select(SourcePassage).where(SourcePassage.organization_id == org_id, SourcePassage.id == row.source_passage_id))
                        if passage_row and row.quoted_excerpt and row.quoted_excerpt.casefold() in passage_row.text.casefold():
                            valid_citations += 1
                print(f"{example['name']}: expected={sorted(expected)} predicted={sorted(predicted)}")
        precision = correct / predicted_total if predicted_total else 1.0
        recall = correct / expected_total if expected_total else 1.0
        citation_validity = valid_citations / citations if citations else 1.0
        false_breach_rate = high_false_breaches / possible_false_breaches if possible_false_breaches else 0.0
        print(json.dumps({"precision": round(precision, 4), "recall": round(recall, 4), "citation_validity": round(citation_validity, 4), "false_breach_rate": round(false_breach_rate, 4), "evaluation_judgement": "fixed insufficient-evidence fixture; no provider is called"}, indent=2))
        return 0 if precision == 1 and recall == 1 and citation_validity == 1 and false_breach_rate == 0 else 1
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
