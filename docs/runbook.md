# Operations runbook

## Release

1. Build and publish immutable web and API image tags from the reviewed commit.
2. Configure `.env.example` variables in the deployment secret manager. Set production `APP_SECRET_KEY` to a unique random value of at least 32 characters, `SESSION_COOKIE_SECURE=true`, the public HTTPS origins, managed PostgreSQL with pgvector, Redis and private S3-compatible storage. Configure trusted proxy CIDRs only when the ingress overwrites forwarding headers.
3. Take a database backup and verify the latest backup is restorable in a separate environment.
4. Run `docker compose -f compose.production.yaml run --rm migrate` (or the platform's release command `alembic upgrade head` in the API image).
5. Roll out the API, worker and web image tags. Verify `/health`, `/ready`, login, a private upload/download and one scan in a non-production tenant.

## Backups and restore

Use managed PostgreSQL point-in-time recovery or scheduled encrypted `pg_dump` backups. Back up object storage with versioning or an equivalent recovery policy; database rows reference stored objects. Redis is operational state for scan jobs and throttling, not the primary data store; queued jobs may need to be recreated after a Redis restore. Test a coordinated database/object restore regularly. The repository does not configure provider-specific backup schedules.

## Rollback

If the release fails before migration, restore the previous image tags. If a migration has run, first inspect whether it is backward-compatible with the previous application version. Restore the pre-release database backup when a safe downgrade is not available; restore corresponding object versions if files changed. Alembic migrations are forward-only unless a revision explicitly defines a tested downgrade. Do not roll application code back across an incompatible schema.

## Triage

- Readiness failure: inspect PostgreSQL and Redis connectivity and credentials.
- Scan stuck: inspect worker logs, Redis queue/dead-letter list, scan status/progress and cancellation flag. Requeue only after checking idempotency/version snapshots.
- LLM issue: provider use is opt-in; inspect prompt version, model, retrieved passage IDs and latency. Never log provider keys or document bodies.
- Request correlation: use the `X-Request-ID` from the client response to find the structured API record.
- Error reporting: configure `SENTRY_DSN` and a conservative `SENTRY_TRACES_SAMPLE_RATE`; no DSN means no Sentry reporting.
