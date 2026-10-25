import hashlib
import hmac
import os
from pathlib import Path
from time import time
from urllib.parse import quote

from app.core.config import get_settings


class LocalStorage:
    def __init__(self) -> None:
        self.root = Path(get_settings().local_storage_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, organization_id: str, object_key: str) -> Path:
        candidate = (self.root / organization_id / object_key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Invalid private object key")
        return candidate

    def put(self, organization_id: str, object_key: str, file, content_type: str) -> str:
        path = self._safe_path(organization_id, object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as target:
            while chunk := file.read(1024 * 1024):
                target.write(chunk)
        return object_key

    def delete(self, organization_id: str, object_key: str) -> None:
        path = self._safe_path(organization_id, object_key)
        path.unlink(missing_ok=True)

    def signed_download_url(self, organization_id: str, object_key: str, ttl_seconds: int) -> str:
        expires = int(time()) + min(ttl_seconds, 900)
        payload = f"{organization_id}:{object_key}:{expires}".encode()
        signature = hmac.new(get_settings().app_secret_key.encode(), payload, hashlib.sha256).hexdigest()
        return f"/api/v1/private-files/{quote(organization_id)}/{quote(object_key)}?expires={expires}&signature={signature}"

    def stream(self, organization_id: str, object_key: str):
        path = self._safe_path(organization_id, object_key)
        def chunks():
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk
        return chunks(), "application/octet-stream"

    def local_path(self, organization_id: str, object_key: str) -> Path | None:
        return self._safe_path(organization_id, object_key)


def safe_filename(original_name: str) -> str:
    del original_name
    return os.urandom(16).hex()
