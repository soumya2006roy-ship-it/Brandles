from collections import defaultdict
from ipaddress import ip_address, ip_network
from threading import Lock
from time import time

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

_memory: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0))
_lock = Lock()
_login_failures: dict[str, tuple[int, float]] = {}
_login_blocks: dict[str, float] = {}


def client_ip(request) -> str:
    """Use forwarding headers only when the direct peer is explicitly trusted."""
    settings = get_settings()
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ip_address(peer)
    except ValueError:
        return peer
    trusted = []
    for network in settings.trusted_proxy_cidrs.split(","):
        try:
            if network.strip():
                trusted.append(ip_network(network.strip(), strict=False))
        except ValueError:
            continue
    if not any(peer_ip in network for network in trusted):
        return str(peer_ip)
    forwarded = request.headers.get("x-forwarded-for", "").split(",")
    for candidate in forwarded:
        try:
            return str(ip_address(candidate.strip()))
        except ValueError:
            continue
    return str(peer_ip)


def _too_many_requests(retry_after: int):
    from fastapi import HTTPException

    return HTTPException(status_code=429, detail="Too many requests. Try again later.", headers={"Retry-After": str(max(1, retry_after))})


def enforce_login_delay(key: str) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        remaining = redis.ttl(f"brandlens:login-block:{key}")
        if remaining > 0:
            raise _too_many_requests(remaining)
    except RedisError:
        if settings.is_production:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Rate limiting is temporarily unavailable.") from None
        now = time()
        with _lock:
            remaining = int(_login_blocks.get(key, 0) - now)
        if remaining > 0:
            raise _too_many_requests(remaining)


def record_login_failure(key: str) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        failures_key = f"brandlens:login-failures:{key}"
        count = redis.incr(failures_key)
        if count == 1:
            redis.expire(failures_key, 86400)
        if count >= 5:
            delay = min(60, 2 ** min(6, count - 4))
            redis.set(f"brandlens:login-block:{key}", "1", ex=delay)
    except RedisError:
        if settings.is_production:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Rate limiting is temporarily unavailable.") from None
        now = time()
        with _lock:
            count, expires_at = _login_failures.get(key, (0, 0))
            if expires_at <= now:
                count, expires_at = 0, now + 86400
            count += 1
            _login_failures[key] = (count, expires_at)
            if count >= 5:
                _login_blocks[key] = now + min(60, 2 ** min(6, count - 4))


def clear_login_failures(key: str) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        redis.delete(f"brandlens:login-failures:{key}", f"brandlens:login-block:{key}")
    except RedisError:
        if settings.is_production:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Rate limiting is temporarily unavailable.") from None
    with _lock:
        _login_failures.pop(key, None)
        _login_blocks.pop(key, None)


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    settings = get_settings()
    limit = max(1, round(limit * settings.rate_limit_multiplier))
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        redis_key = f"brandlens:rate:{key}"
        value = redis.incr(redis_key)
        if value == 1:
            redis.expire(redis_key, window_seconds)
        if value > limit:
            retry_after = redis.ttl(redis_key)
            raise _too_many_requests(retry_after if retry_after > 0 else window_seconds)
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
                raise _too_many_requests(int(reset_at - now)) from None
            _memory[key] = (count + 1, reset_at)
