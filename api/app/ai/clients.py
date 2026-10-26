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


def get_llm_client(organization: Organization) -> LLMClient:
    settings = get_settings()
    if not settings.allow_workspace_llm or not organization.llm_processing_allowed:
        raise LLMDisabledError("This workspace has not allowed external AI processing.")
    raise RuntimeError("The configured LLM provider has no adapter in this product phase.")


def get_embedding_client(organization: Organization) -> EmbeddingClient:
    settings = get_settings()
    if not settings.allow_workspace_llm or not organization.llm_processing_allowed:
        raise LLMDisabledError("This workspace has not allowed external AI processing.")
    raise RuntimeError("The configured embedding provider has no adapter in this product phase.")
