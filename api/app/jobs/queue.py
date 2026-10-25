import json
from typing import Any

from redis import Redis

from app.core.config import get_settings

QUEUE_NAME = "brandlens:jobs"


def enqueue(task: str, payload: dict[str, Any]) -> None:
    client = Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2)
    client.rpush(QUEUE_NAME, json.dumps({"task": task, "payload": payload}))
