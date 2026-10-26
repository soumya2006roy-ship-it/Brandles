import json
import logging
import time

from redis import Redis

from app.core.config import get_settings
from app.jobs.queue import QUEUE_NAME
from app.campaigns.scans import execute_campaign_scan
from app.data_controls import purge_expired_scan_history
from app.observability import increment, log_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brandlens.worker")


def run() -> None:
    client = Redis.from_url(get_settings().redis_url)
    next_retention_run = time.monotonic() + 3600
    logger.info("BrandLens worker is waiting for jobs")
    while True:
        wait_seconds = max(1, min(3600, int(next_retention_run - time.monotonic())))
        result = client.blpop(QUEUE_NAME, timeout=wait_seconds)
        raw_job = result[1] if result else None
        if raw_job is not None:
            try:
                job = json.loads(raw_job)
                task_name = job.get("task", "unknown") if isinstance(job, dict) else "invalid"
            except (json.JSONDecodeError, UnicodeDecodeError):
                task_name = "invalid"
                job = {}
            try:
                if task_name == "campaign_scan":
                    payload = job.get("payload", {})
                    increment("jobs_started_total")
                    execute_campaign_scan(str(payload["organization_id"]), str(payload["scan_id"]))
                    increment("jobs_completed_total")
                else:
                    client.rpush("brandlens:dead-letter", json.dumps({"task": task_name, "raw": raw_job}))
                    logger.warning("No handler registered for job type %s; moved it to the dead-letter queue", task_name)
            except Exception:
                increment("jobs_failed_total")
                logger.exception("Background job %s failed", task_name)
        if time.monotonic() >= next_retention_run:
            try:
                removed = purge_expired_scan_history()
                logger.info("Retention job removed %s expired scan records", removed)
            except Exception:
                logger.exception("Retention job failed")
            next_retention_run = time.monotonic() + 3600


if __name__ == "__main__":
    run()
