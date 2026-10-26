"""Small process-local counters and JSON request logging hooks."""

import json
import logging
from threading import Lock
from time import monotonic

_lock = Lock()
_counters: dict[str, float] = {
    "http_requests_total": 0,
    "http_errors_total": 0,
    "jobs_started_total": 0,
    "jobs_completed_total": 0,
    "jobs_failed_total": 0,
    "llm_calls_total": 0,
    "llm_cost_usd_total": 0,
    "llm_latency_seconds_total": 0,
    "http_request_duration_seconds_total": 0,
}


def increment(name: str, amount: float = 1) -> None:
    if name not in _counters:
        return
    with _lock:
        _counters[name] += amount


def metric_snapshot() -> dict[str, float]:
    with _lock:
        return dict(_counters)


def log_json(logger: logging.Logger, message: str, **fields) -> None:
    logger.info(json.dumps({"message": message, **fields}, separators=(",", ":"), default=str))


def request_started() -> float:
    return monotonic()
