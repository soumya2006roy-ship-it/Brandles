"""Strict response validation and local vector retrieval for judgement checks."""

from math import sqrt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BrandGuidelineSource, SourcePassage
from app.sources.documents import local_hash_embedding


class JudgementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    verdict: Literal["breach", "compliant", "insufficient_evidence"]
    flagged_text: str | None
    source_id: str | None
    quoted_excerpt: str | None
    rationale: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    suggested_fix: str | None


def parse_judgement(value: dict, *, asset_text: str, retrieved: list[dict]) -> JudgementResponse:
    """Validate strict output and reject invented spans or citations."""
    result = JudgementResponse.model_validate(value)
    if result.verdict == "breach":
        if not result.flagged_text or result.flagged_text.casefold() not in asset_text.casefold():
            raise ValueError("The flagged text does not occur in the scanned asset.")
        passage = next((item for item in retrieved if item["source_id"] == result.source_id), None)
        if not passage or not result.quoted_excerpt or result.quoted_excerpt.casefold() not in passage["text"].casefold():
            raise ValueError("The citation is missing or the quoted excerpt is not present in the cited passage.")
    elif result.verdict == "compliant":
        passage = next((item for item in retrieved if item["source_id"] == result.source_id), None)
        if not passage or not result.quoted_excerpt or result.quoted_excerpt.casefold() not in passage["text"].casefold():
            raise ValueError("A compliant judgement must cite a retrieved approved passage.")
    elif result.verdict == "insufficient_evidence" and (result.source_id is not None or result.quoted_excerpt is not None):
        raise ValueError("Insufficient evidence responses cannot cite an unverified passage.")
    return result.model_copy(update={"confidence": min(result.confidence, 0.95)})


def retrieve_top_passages(db: Session, organization_id: str, query: str, as_of) -> list[dict]:
    """Rank effective approved passages with the stored deterministic lexical-hash vectors."""
    rows = db.execute(
        select(SourcePassage, BrandGuidelineSource)
        .join(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id))
        .where(SourcePassage.organization_id == organization_id, BrandGuidelineSource.status == "approved", BrandGuidelineSource.deleted_at.is_(None), (BrandGuidelineSource.effective_from.is_(None) | (BrandGuidelineSource.effective_from <= as_of)), (BrandGuidelineSource.effective_to.is_(None) | (BrandGuidelineSource.effective_to >= as_of)))
    ).all()
    query_vector = local_hash_embedding(query)
    ranked = []
    for passage, source in rows:
        vector = passage.embedding or local_hash_embedding(passage.text)
        dot = sum(left * right for left, right in zip(query_vector, vector, strict=False))
        norm = sqrt(sum(value * value for value in query_vector) * sum(value * value for value in vector)) or 1
        ranked.append((dot / norm, passage, source))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return [{"passage_id": passage.id, "source_id": source.id, "source_title": source.title, "source_version": source.version, "text": passage.text, "similarity": round(score, 6)} for score, passage, source in ranked[:5]]
