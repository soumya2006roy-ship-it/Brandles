from collections import defaultdict
from threading import Lock
from time import time

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

_memory: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0))
_lock = Lock()


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        value = redis.incr(f"brandlens:rate:{key}")
        if value == 1:
            redis.expire(f"brandlens:rate:{key}", window_seconds)
        if value > limit:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    except RedisError:
        if settings.is_production:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Rate limiting is temporarily unavailable.") from None
        now = time()
        with _lock:
            count, reset_at = _memory[key]
            if reset_at <= now:
                count, reset_at = 0, now + window_seconds
            if count >= limit:
                from fastapi import HTTPException

                raise HTTPException(status_code=429, detail="Too many requests. Try again later.") from None
            _memory[key] = (count + 1, reset_at)
