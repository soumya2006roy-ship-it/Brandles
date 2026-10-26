from typing import Any, Protocol

from app.core.config import get_settings
from app.db.models import Organization


class LLMDisabledError(RuntimeError):
    pass


class LLMClient(Protocol):
    vendor: str
    model: str

    def judge(self, task: str, approved_passages: list[dict[str, str]], asset_excerpt: str) -> dict[str, Any]: ...


class EmbeddingClient(Protocol):
    vendor: str
    model: str

    def embed(self, passages: list[str]) -> list[list[float]]: ...


class MockLLMClient:
    vendor = "mock"
    model = "mock-v1"

    def judge(self, task: str, approved_passages: list[dict[str, str]], asset_excerpt: str) -> dict[str, Any]:
        del task, approved_passages
        del asset_excerpt
        return {"verdict": "insufficient_evidence", "flagged_text": None, "source_id": None, "quoted_excerpt": None, "rationale": "The mock model does not make content judgements.", "confidence": 0.0, "suggested_fix": None}


class MockEmbeddingClient:
    vendor = "mock"
    model = "mock-hash-v1"

    def embed(self, passages: list[str]) -> list[list[float]]:
        del passages
        raise RuntimeError("No embedding provider is configured. Use retrieval by exact terms until one is enabled.")


def get_llm_client(organization: Organization) -> LLMClient:
    settings = get_settings()
    if not settings.allow_workspace_llm or not organization.llm_processing_allowed:
        raise LLMDisabledError("This workspace has not allowed external AI processing.")
    if settings.llm_provider == "mock":
        return MockLLMClient()
    raise RuntimeError("The configured LLM provider has no adapter in this product phase.")


def get_embedding_client(organization: Organization) -> EmbeddingClient:
    settings = get_settings()
    if not settings.allow_workspace_llm or not organization.llm_processing_allowed:
        raise LLMDisabledError("This workspace has not allowed external AI processing.")
    if settings.embedding_provider == "mock":
        return MockEmbeddingClient()
    raise RuntimeError("The configured embedding provider has no adapter in this product phase.")
