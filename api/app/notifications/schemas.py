from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    kind: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
