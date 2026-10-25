import json
import logging

from redis import Redis

from app.core.config import get_settings
from app.jobs.queue import QUEUE_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brandlens.worker")


def run() -> None:
    client = Redis.from_url(get_settings().redis_url)
    logger.info("BrandLens worker is waiting for jobs")
    while True:
        _, raw_job = client.blpop(QUEUE_NAME)
        try:
            job = json.loads(raw_job)
            task_name = job.get("task", "unknown") if isinstance(job, dict) else "invalid"
        except (json.JSONDecodeError, UnicodeDecodeError):
            task_name = "invalid"

        # Keep unhandled work available for diagnosis until workflow handlers exist.
        client.rpush("brandlens:dead-letter", json.dumps({"task": task_name, "raw": raw_job}))
        logger.warning("No handler registered for job type %s; moved it to the dead-letter queue", task_name)


if __name__ == "__main__":
    run()
