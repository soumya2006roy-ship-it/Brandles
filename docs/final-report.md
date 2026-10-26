# BrandLens delivery report

Date: 2026-10-26

## Delivery by phase

| Phase | Delivered |
| --- | --- |
| 1 | Organisation workspace foundation and product structure. Commit `6d9245c`. |
| 2 | Approved source uploads/versioning, passage parsing/provenance, effective dates, source search/history and evidence-linked rules. Commit `91121c0`. |
| 3 | Campaigns, channel assets, content-based validation, versioning, stale-scan invalidation, metadata stripping, optional OCR/malware checks and approved-logo matching. Commit `6d06906`. |
| 4 | Deterministic exact checks, evidence-constrained judgement parsing/fallback, campaign fact comparison, resumable/cancellable scans, labelled mock evaluation set. Commit `beb614a`. |
| 5 | Findings, creator resolution, version-bound reviewer decisions, idempotent submissions, derived campaign status and notifications. Commit `b296a03`. |
| 6 | Evidence Map, date validity warnings, suggested guideline updates, bounded source-only Brand Twin, Hindi prototype and platform preview prototype. Commit `5f033d8`. |
| 7 | Organisation dashboard, campaigns/assets/findings/reviews/sources/rules/audit/team/admin surfaces and read-only sample workspace. Commit `0920d8f`. |
| 8 | Tenant/RBAC protections, origin checks, security headers, Redis-backed limits, upload access controls, append-only audit and data export/deletion/retention. Commit `6708475`. |
| 9 | Vitest and Playwright/axe setup, concurrency and workflow assertions, PostgreSQL integration test, CI jobs, request IDs/JSON logs, health/readiness/metrics, optional Sentry hook and npm dependency audit cleanup. Commit `132b03a`. |
| 10 | Production Next.js image and Python API/worker image, production Compose release migration service, complete environment example, architecture/API/security/runbook/evaluation/admin docs and this report. This report is included in the final Phase 10 commit. |

Phase 9 CI is configured, not observed on GitHub in this run. The full signup-to-approved-campaign journey is not automated end-to-end through the browser; only public-page/sample-workspace browser checks are run locally. Do not treat that acceptance item as demonstrated.

### Files changed in Phases 9–10

- Phase 9: `.github/workflows/ci.yml`, `package.json`/lockfile, `vitest.config.ts`, `playwright.config.ts`, `e2e/public-pages.spec.ts`, `lighthouserc.json`, `pytest.ini`, API observability/rate-limit/runtime modules and tests, regenerated `api/openapi.json` and `app/lib/api-schema.d.ts`, findings filter helper/tests, `.env.example`, `README.md` and `docs/decisions.md`.
- Phase 10: `.dockerignore`, `Dockerfile.web`, `api/Dockerfile`, `compose.production.yaml`, `next.config.ts`, `.env.example`, `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/security.md`, `docs/runbook.md`, `docs/evaluation.md`, `docs/admin-guide.md` and this report.
- These phases add no database migration; the latest schema remains revision `0008_retention_controls`.

## Schema and migrations

Alembic migrations are in `api/alembic/versions`; the latest revision is `0008_retention_controls`. Apply migrations from the API directory:

```powershell
Push-Location api
.venv\Scripts\alembic.exe upgrade head
Pop-Location
```

In the production Compose configuration, the one-shot migration service is the release gate:

```powershell
docker compose -f compose.production.yaml run --rm migrate
```

This migration step and Docker image have not been executed here because Docker is unavailable. A fresh Postgres migration/trigger test is configured in GitHub Actions but was skipped locally.

## Verification results

| Command/check | Result |
| --- | --- |
| `npm run lint` | Passed. |
| `npm run typecheck` | Passed. |
| `npm test` | Passed: 2 Vitest tests. |
| `npm run build` | Passed. Built-in light/dark token contrast checks passed; Lighthouse itself was not run locally. |
| `npm run test:e2e` | Passed: 3 Chromium tests, including axe on `/`, `/features`, `/security` and `/privacy`. |
| `api\.venv\Scripts\python.exe -m pytest -q` | Passed twice: 45 passed, 1 skipped; latest run completed in 345.12s. The skipped check requires a PostgreSQL database; one Starlette/httpx deprecation warning remains. |
| `api\.venv\Scripts\python.exe api\scripts\run_evals.py` | Passed the three labeled examples: precision 1.0, recall 1.0, cited excerpt validity 1.0, false-breach rate 0.0. These are mock-only results on a small set. |
| `npm audit --audit-level=high` | Passed: 0 known vulnerabilities in the installed npm dependency tree. |
| `api\.venv\Scripts\python.exe -m pip_audit -r api/requirements.txt` | Passed: no known vulnerabilities found. |
| `git diff --check` | Passed. |
| YAML parse (`compose.production.yaml`, `.github/workflows/ci.yml`) | Passed with PyYAML. |
| PostgreSQL integration/migration check | Skipped locally; Docker and a `TEST_DATABASE_URL` were unavailable. CI is configured to run it against a clean PostgreSQL/pgvector service. |
| Lighthouse 95+ | CI is configured with 0.95 category score assertions on four public pages; it was not run locally or on GitHub during this delivery. |
| Docker Compose validation/startup | Not run: `docker` is not installed in this environment. |

## Security and residual risks

Implemented controls and test references are described in [security.md](security.md). Local unit tests exercise tenant scoping, roles, self-review denial, verification gating, invite expiry/use limits, concurrent fallback throttling, upload restrictions, prompt-injection handling, audit immutability and review version binding. The PostgreSQL audit trigger and migration integration remains unverified locally.

Operational metrics are process-local and reset on restart; they are not a durable metrics backend. LLM cost stays zero until a real provider adapter reports token usage. Sentry is opt-in. Production encryption, backups, TLS between managed services, secret rotation, object-store lifecycle, alerting and restore drills remain deployment responsibilities. CI, Lighthouse thresholds and secret scanning are configured but require an actual GitHub Actions run to produce results.

The approval acceptance scenario is not fully demonstrated. The eval set covers a 20% versus 30% discount conflict, unsupported skincare claims and adversarial text, but it does not prove that the requested wrong-logo and post-30-Nov expiry findings each have citations in one complete seeded UI journey. Exact logo matching and expiry warnings have unit/API coverage; semantic logo matching remains prototype behavior.

## Prototypes and limitations

- Vectors are deterministic lexical-hash vectors, not semantic embeddings.
- No live LLM provider adapter is included. Judgement remains disabled unless a provider adapter and organisation consent are supplied; failures fall back to human verification.
- OCR requires a configured provider/tool. Malware scanning requires a configured scanner. Neither is enabled by default.
- Hindi checking and Instagram/LinkedIn-style previews are limited rule-based prototypes.
- Cost metrics are placeholders until an adapter reports cost. Campaign scans and jobs are not instrumented into a shared external metrics service.
- Lighthouse and PostgreSQL integration are configured for CI, but no CI run is available in this report.

## Configuration and operator input

Before a production launch, provide:

- Public domain, HTTPS ingress, `NEXT_PUBLIC_SITE_URL`, `FRONTEND_ORIGIN`, `BRANDLENS_BACKEND_URL`, trusted proxy CIDRs and secure cookies.
- Managed PostgreSQL with pgvector and Redis connection URLs.
- A secret-manager value for `APP_SECRET_KEY` (unique, random, at least 32 characters).
- Private S3-compatible endpoint, bucket, region and access credentials.
- Resend API key and a verified sender, or a production SMTP service.
- If AI is approved: provider adapter, model and key; explicit workspace consent; vendor DPA and privacy/legal review. No key alone enables an unimplemented adapter.
- Optional OCR and malware-scanning tools/services, plus `SENTRY_DSN` if external error reporting is desired.
- Legal review of Terms and Privacy statements and a documented retention/backup policy.

See `.env.example`, [runbook.md](runbook.md), [architecture.md](architecture.md) and [admin-guide.md](admin-guide.md).

## Run and deploy

For local checks, use the commands in `README.md`. With Docker, the existing `docker-compose.yml` is the development stack. Production services use `Dockerfile.web`, `api/Dockerfile` (also used for the worker) and `compose.production.yaml`; configure the required managed services and secrets first, run the migration service, then deploy the immutable web/API images behind a TLS reverse proxy. Back up PostgreSQL and object storage before release and follow [runbook.md](runbook.md) for rollback and restore steps. This deployment path is documented but unverified in this environment.

## Evidence-based score

**Overall: 6.7/10** using the requested weights.

| Area | Score | Weight | Evidence and limit |
| --- | ---: | ---: | --- |
| Functionality | 6.5/10 | 30% | Core source-to-campaign-to-review APIs and UI exist; the complete UI journey and all skincare acceptance findings are not demonstrated, and no real LLM adapter is available. |
| Security | 6.5/10 | 25% | Tenant/RBAC/security tests and append-only audit controls exist; Postgres isolation/trigger behavior and production deployment were not exercised locally. |
| UX | 7.5/10 | 20% | Responsive product screens, dark theme and public axe checks pass; authenticated product-page keyboard/axe coverage is incomplete. |
| Testing | 6.0/10 | 15% | 45 API tests, 2 unit tests, 3 browser checks and a small mock eval pass; one DB integration check is skipped, and CI/Lighthouse have not run. |
| Maintainability | 7.0/10 | 10% | Migrations, generated API schema, phase commits and operational docs are maintained; Docker images and production Compose remain unverified. |

Weighted result: `6.5×0.30 + 6.5×0.25 + 7.5×0.20 + 6.0×0.15 + 7.0×0.10 = 6.675`, reported as **6.7/10**.
