# BrandLens delivery report

Date: 2026-10-26

## Delivery by phase

| Phase | Delivered |
| --- | --- |
| 1 | Organisation workspace foundation and product structure. Commit `6d9245c`. |
| 2 | Approved source uploads/versioning, passage parsing/provenance, effective dates, source search/history and evidence-linked rules. Commit `91121c0`. |
| 3 | Campaigns, channel assets, content-based validation, versioning, stale-scan invalidation, metadata stripping, optional OCR/malware checks and approved-logo matching. Commit `6d06906`. |
| 4 | Deterministic exact checks, evidence-constrained judgement parsing/fallback, campaign fact comparison, resumable/cancellable scans, labelled evaluation set. Commit `beb614a`. |
| 5 | Findings, creator resolution, version-bound reviewer decisions, idempotent submissions, derived campaign status and notifications. Commit `b296a03`. |
| 6 | Evidence Map, date validity warnings, suggested guideline updates, bounded source-only Brand Twin, Hindi prototype and platform preview prototype. Commit `5f033d8`. |
| 7 | Organisation dashboard, campaigns/assets/findings/reviews/sources/rules/audit/team/admin surfaces. Commit `0920d8f`. |
| 8 | Tenant/RBAC protections, origin checks, security headers, Redis-backed limits, upload access controls, append-only audit and data export/deletion/retention. Commit `6708475`. |
| 9 | Vitest and Playwright/axe setup, concurrency and workflow assertions, PostgreSQL integration test, CI jobs, request IDs/JSON logs, health/readiness/metrics, optional Sentry hook and npm dependency audit cleanup. Commit `132b03a`. |
| 10 | Production Next.js image and Python API/worker image, production Compose release migration service, complete environment example, architecture/API/security/runbook/evaluation/admin docs and this report. This report is included in the final Phase 10 commit. |

Phase 9 CI is configured, not observed on GitHub in this run. The full signup-to-approved-campaign journey is not automated end-to-end through the browser; local checks cover public pages and selected account-entry behavior only. Do not treat that acceptance item as verified.

### Files changed in Phases 9–10

- Phase 9: `.github/workflows/ci.yml`, `package.json`/lockfile, `vitest.config.ts`, `playwright.config.ts`, `e2e/public-pages.spec.ts`, `lighthouserc.json`, `pytest.ini`, API observability/rate-limit/runtime modules and tests, regenerated `api/openapi.json` and `app/lib/api-schema.d.ts`, findings filter helper/tests, `.env.example`, `README.md` and `docs/decisions.md`.
- Phase 10: `.dockerignore`, `Dockerfile.web`, `api/Dockerfile`, `compose.production.yaml`, `next.config.ts`, `.env.example`, `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/security.md`, `docs/runbook.md`, `docs/evaluation.md`, `docs/admin-guide.md` and this report.
- The original Phases 9–10 added no database migration; the latest schema is now revision `0009_remove_public_workspace_marker`, added during the website cleanup. It tombstones previously marked example organizations before dropping the obsolete marker. Apply it with the usual `alembic upgrade head` release step; it has not been applied in this environment.

## Schema and migrations

Alembic migrations are in `api/alembic/versions`; the latest revision is `0009_remove_public_workspace_marker`. Apply migrations from the API directory:

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
| `api\.venv\Scripts\python.exe api\scripts\run_evals.py` | Passed the three labeled examples: precision 1.0, recall 1.0, cited excerpt validity 1.0, false-breach rate 0.0. These are fixture-only results on a small set. |
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

The approval acceptance scenario is not fully verified. The evaluation set covers a 20% versus 30% discount conflict, unsupported skincare claims and adversarial text, but it does not prove that the requested wrong-logo and post-30-Nov expiry findings each have citations in one complete UI journey. Exact logo matching and expiry warnings have unit/API coverage; semantic logo matching remains prototype behavior.

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
| Functionality | 6.5/10 | 30% | Core source-to-campaign-to-review APIs and UI exist; the complete UI journey and all skincare acceptance findings are not verified, and no real LLM adapter is available. |
| Security | 6.5/10 | 25% | Tenant/RBAC/security tests and append-only audit controls exist; Postgres isolation/trigger behavior and production deployment were not exercised locally. |
| UX | 7.5/10 | 20% | Responsive product screens, dark theme and public axe checks pass; authenticated product-page keyboard/axe coverage is incomplete. |
| Testing | 6.0/10 | 15% | 45 API tests, 2 unit tests, 3 browser checks and a small fixture evaluation pass; one DB integration check is skipped, and CI/Lighthouse have not run. |
| Maintainability | 7.0/10 | 10% | Migrations, generated API schema, phase commits and operational docs are maintained; Docker images and production Compose remain unverified. |

Weighted result: `6.5×0.30 + 6.5×0.25 + 7.5×0.20 + 6.0×0.15 + 7.0×0.10 = 6.675`, reported as **6.7/10**.

## Website audit follow-up (2026-10-26)

The additional website audit uses the separate rubric in the pasted master prompt. The existing Phase 1–10 score above is retained as a record of the product delivery assessment.

### Important findings and fixes

- Fixed production startup: `npm start` now runs Next's generated standalone server, and the build prepares standalone static and public assets. A production server run returned 200 for `/`, `/icon-192.png`, `/robots.txt` and `/sitemap.xml`, and 404 for an unknown route. Production theme hydration and four public routes passed browser/axe checks.
- Replaced the contact form's process-local, spoofable `X-Forwarded-For` limiter with atomic Redis throttling in production, an IP digest in Redis keys, a bounded development fallback, `Retry-After`, and fail-closed production behavior when Redis or a valid trusted `X-Real-IP` is unavailable. The ingress must overwrite `X-Real-IP`.
- Removed the public fictional workspace route, seed API and browser-only campaign state. Account, invite and contact links now lead to actual product entry points. Runtime judgement-provider substitutes were removed; the deterministic evaluation fixture remains isolated to the evaluation script.
- Added focused contact limiter unit and browser coverage. The browser test confirmed validation feedback, five accepted-to-limiter requests followed by 429, and that rotating `X-Forwarded-For` does not change the rate-limit key. No Resend key is configured, so the first five API attempts returned expected 503 responses rather than sending mail.
- Added `docs/audit-report.md` and `docs/requirements-matrix.md`. Their Partial statuses identify the checks that still need a full route crawl, provider credentials, CI, Docker or manual device testing.

### Audit verification

| Command/check | Result |
| --- | --- |
| `npm run lint` | Passed. |
| `npm run typecheck` | Passed. |
| `npm test` | Passed: 5 tests across 2 files. |
| `npm run build` | Passed, including light/dark contrast token checks and standalone asset preparation. |
| `npm run test:e2e` against local dev server | Passed: 5 Chromium tests, including contact validation/rate limiting and axe on four public routes. |
| Production `npm run start`, route and asset smoke | Passed: home and icons/robots/sitemap returned 200; unknown route returned 404. |
| Production browser smoke against the standalone server | Passed before Phase 2: 4 checks on public pages and the former unauthenticated workspace. This run predates route removal and is not the current result. |
| `npm audit --audit-level=high` | Passed: 0 known vulnerabilities. |

### Remaining verification and risks

- The 21-item matrix is not fully green. Social image dimensions/content, route-wide metadata uniqueness, JSON-LD validity/parity, internal link crawl, AVIF/WebP response format, consent network behavior, reduced motion, full keyboard coverage, 320–400% zoom and responsive widths need additional browser checks.
- Lighthouse was not run locally; no 95+ scores are claimed. CI thresholds are configuration, not a recorded Lighthouse result. Product routes were not covered by axe in this audit.
- Redis production behavior was not verified against a running Redis service. Contact email delivery, Resend confirmation, payload/header injection, honeypot and 413 were not exercised here. Set `REDIS_URL` and ensure ingress overwrites `X-Real-IP` before deployment.
- Docker, the API/Postgres stack and the complete signup-to-approved-campaign journey were not run in this audit. Full stack verification still requires Docker Desktop and a clean migrated PostgreSQL instance.
- Some production-run asset requests during the audit surfaced a local Windows standalone Sharp optional-runtime warning on shutdown. Core page hydration, CSS/JS and direct public icon requests passed; optimized image delivery still needs a clean production-container check.

### Website audit score

**5.9/10**, using the pasted prompt's weighted rubric. This reflects the uncompleted verification requirements; it is not a score for the prior Phase 1–10 product build.

| Category | Score | Weight | Evidence |
| --- | ---: | ---: | --- |
| Requirements completeness and correctness | 4.0/10 | 25% | 21 checks are inventoried, but most remain Partial pending broad runtime verification. |
| Content truth and product fidelity | 7.5/10 | 15% | Public copy now links to account, invite and contact entry points; unsupported fixed confidence values and the unauthenticated workspace route were removed. Full proposal line-by-line review remains incomplete. |
| Security, privacy and consent | 6.0/10 | 20% | Production headers and contact limiter improvements were verified; consent network behavior, mail abuse paths and live Redis are not. |
| UI/UX and design quality | 7.5/10 | 15% | Theme icon toggling, account entry links, four public-page smoke checks and axe pass; no full responsive or human visual review. |
| Accessibility and performance | 5.0/10 | 15% | Axe passed four public pages and contrast token pairs pass; Lighthouse, all routes/themes, keyboard and zoom remain unverified. |
| Maintainability and test coverage | 6.5/10 | 10% | Focused tests and docs were added; the full CI, production container and route-wide acceptance suite were not run. |

Weighted result: `4.0×0.25 + 7.5×0.15 + 6.0×0.20 + 7.5×0.15 + 5.0×0.15 + 6.5×0.10 = 5.85`, reported as **5.9/10**.

## Public workspace removal and launcher implementation (2026-10-26)

- Phase 1 diagnosis was committed as `56da172`; Phase 2 removed the unauthenticated workspace UI/API/seed path, removed runtime provider substitutes, updated public calls to account/invite/contact entry points, regenerated the API contract, added a forward migration and internal-route checks in commit `40382d7`.
- Phase 3 adds `/signup`, `/org/create` and `/join`, redirects signed-out `/app/*` access to `/login`, and uses the same-origin API proxy with a configured server-side API URL. Commit: `8dc5d95`.
- Phase 4 creates `start.bat`, cross-platform `start.sh` and `npm run dev:all`, a named API/worker/web process launcher with file logs, `.env` secret generation, lock-hash dependency setup, data-container health checks, migrations, first-admin bootstrap, production mode, stop and typed-confirmation reset scripts. The old Windows entry point delegates to the new one. Commit: `88ebc87`.
- The interactive API documentation route was aligned to `/docs`; `/api/openapi.json` remains available in development. Added an idempotent local bootstrap CLI test and API health/docs tests.
- At the initial audit Docker CLI was unavailable, so the launcher stopped at its Docker prerequisite. The follow-up Docker verification below supersedes that limitation for Windows development startup, health, migrations and stop behavior.
- The pre-cleanup evaluation result remains a small evaluation-only fixture result (3 examples: precision 1.0, recall 1.0, citation validity 1.0, false-breach rate 0.0). It does not validate a live model or a complete browser workflow.
- At the initial audit, `npm run lint`, `npm run typecheck`, and `npm run build` passed; `npm test` passed (5); `npm run test:e2e` passed (6); `npm run check:links` passed (32 routes plus metadata assets); API pytest passed (47 passed, 1 skipped); and an isolated SQLite API smoke returned 200 for `/health`, `/docs`, and `/api/openapi.json`. `npm run dev:all` and `start.bat` stopped with the Docker prerequisite message. See the Docker verification update below for current results.

## Docker verification update (2026-10-26)

Docker Desktop was subsequently available in the user environment. The Windows development launcher started PostgreSQL/pgvector, Redis, Mailpit, API, worker and web; migrations reached `0009_remove_public_workspace_marker`; the bootstrap admin was created; readiness reported the database and Redis healthy; and a second launch was idempotent. `stop.bat` and `stop.bat containers` were exercised; containers stopped and their volumes were preserved. The old MinIO image could not be pulled, so local development now uses private local-file storage. This supersedes the Docker-unavailable statement above for the current Windows run.

With `TEST_DATABASE_URL` set to the local PostgreSQL service, API pytest passed all 48 tests including the Postgres migration/audit check. Vitest passed 5, Playwright passed 6, link checks covered 32 routes/assets, and evaluation fixtures reported precision 1.0, recall 1.0, citation validity 1.0, and false-breach rate 0.0. `npm run lint` and `npm run typecheck` passed. `npm run build` did not complete: Next.js hit `EPERM` unlinking generated output in the OneDrive checkout. Production mode, destructive reset and the full signup-to-approved-campaign journey therefore remain unverified. See [launch-verification.md](launch-verification.md).

## Final simulation status (2026-10-26)

The latest top-to-bottom verification, three passes, exact command results, journey table and evidence-based score are recorded in [final-simulation-report.md](final-simulation-report.md). That report supersedes the earlier audit-only score and the earlier OneDrive build limitation above. The complete UI acceptance journey, Lighthouse threshold, exhaustive adversarial matrix and live-provider paths remain unverified.
