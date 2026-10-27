# Final top-to-bottom simulation report

Date: 2026-10-27. This report supersedes earlier partial launch/build statements in `docs/final-report.md` and `docs/launch-verification.md`. The running pass log is [simulation-log.md](simulation-log.md); endpoint inventory is [endpoint-matrix.md](endpoint-matrix.md); the public-site requirements inventory is [requirements-matrix.md](requirements-matrix.md).

## Scope and results

Four passes were recorded. No P0 issue was found. The P1s found in the code/config checks were fixed; important end-user acceptance paths remain unverified, so this is not a declaration that the requested product is complete.

| Pass | P0 | P1 | P2 | Main findings |
|---|---:|---:|---:|---|
| 1 — static sweep | 0 | 1 | 0 | Repeat build failed with Windows `EPERM` in OneDrive; fixed with guarded generated-output cleanup. |
| 2 — cold start | 0 | 0 | 2 | PowerShell misformatted normal service logs; fixed. One old-container port rebind failed once, then the next launch succeeded. |
| 3 — security/contract regression | 0 | 2 | 1 | Development Compose exposed ports on all interfaces and had a weak signing-key fallback; fixed. OpenAPI omitted cookie auth; fixed. Two external links lacked explicit `noopener`; fixed. |
| 4 — current checkout regression | 0 | 0 | 0 | Build, lint, typecheck, frontend/API tests and mock evaluations passed. Docker was unavailable; pip-audit could not resolve a dependency from the configured package index. Removed one stale demo-mode comment. |

Pass 4 results (2026-10-27): `npm run lint`, `npm run typecheck`, `npm run build`, `npm test` (5 passed), `npm run test:e2e` (6 passed), API pytest (48 passed, 1 PostgreSQL integration skipped), and the 3-case deterministic evaluation passed. `npm audit --audit-level=high` found 0 vulnerabilities. `pip-audit` was inconclusive because the configured package index did not provide `sentry-sdk<3,>=2.0`; do not treat this as a clean dependency audit. The tracked-file credential-pattern fallback found no matches. Docker was unavailable, and full journeys, migration integration and chaos checks remain unverified. Full output and limitations are recorded in `docs/simulation-log.md`.

### Fix commits

- `4779a98` — repeatable production build on Windows.
- `897aa4a` — OpenAPI cookie-auth contract, loopback-only Compose ports, required local signing secret, service log normalization, endpoint matrix and documentation updates.
- `56dceec` — explicit `noopener noreferrer` on external organisation links.

## Files and schema changes

- No database schema migration was added in this simulation pass. Existing migrations `0001`–`0009` applied to the empty test database; the retained local database passed `alembic check`. OpenAPI security metadata changed, and `api/openapi.json` plus `app/lib/api-schema.d.ts` were regenerated.
- `4779a98`: `package.json`, `scripts/clean-next-build.mjs`.
- `897aa4a`: `README.md`, `api/app/main.py`, `api/openapi.json`, `api/tests/test_health.py`, `docker-compose.yml`, `docs/endpoint-matrix.md`, `docs/launch-verification.md`, `docs/requirements-matrix.md`, `scripts/run-service.ps1`.
- `56dceec`: `app/app/admin/verifications/verification-queue.tsx`, `app/app/organisations/organisation-workspace.tsx`.
- Final documentation commit: `docs/architecture.md`, `docs/final-report.md`, `docs/security.md`, `docs/final-simulation-report.md`, `docs/simulation-log.md`.

## Verification evidence

### Cold start and launch

To avoid deleting the user’s ignored `.env` files or existing database, the cold-start run used a new source export in `%TEMP%` with a distinct Compose project name and free test ports. The export started with no local env files, dependencies, logs or build output. It installed 488 npm packages, created a fresh Python venv, installed API requirements, created empty Postgres/Redis volumes, ran migrations from `0001` to `0009`, bootstrapped the first administrator, and started the web, API and worker.

The first launch and production-mode launch completed. A second `start.bat` reported the healthy existing app and did not duplicate services. `stop.bat` freed ports 3000 and 8000. Web home, API `/health`, `/ready`, `/docs`, and Mailpit returned 200; readiness returned `{"status":"ready","checks":{"database":true,"redis":true}}`. The isolated test volumes were removed afterward. The original `hackathon_postgres_data` and `hackathon_redis_data` volumes were retained.

After the Compose hardening, the existing local stack was recreated against those same volumes. Docker reported Postgres, Redis and Mailpit healthy, with published addresses `127.0.0.1:55432`, `127.0.0.1:16379`, `127.0.0.1:18025`, and `127.0.0.1:11025`. One first rebind attempt failed because Windows still held the previous port; the launcher stopped cleanly, and the next run succeeded. The app processes were stopped after verification; the original data containers remain running as they were before this task.

### Exact checks and results

| Command/check | Result |
|---|---|
| `npm run lint` | Passed after final source changes. |
| `npm run typecheck` | Passed after OpenAPI client regeneration and final source changes. |
| `npm run build` | Passed repeatedly in the OneDrive checkout; the contrast script passed its configured light/dark token pairs and the standalone runtime was prepared. |
| `npm test` | 5 passed across 2 files. |
| `npm run test:e2e` | 6 Chromium tests passed. Includes key public-page loading, account entry points, retired `/demo` check, theme icon change, contact validation/429, and axe checks on key public pages. |
| `npm run check:links` | 32 internal routes and required metadata assets passed on the production server. |
| `api\\.venv\\Scripts\\python.exe -m pytest -q` with local `TEST_DATABASE_URL` | 49 passed in 302.08 seconds; one existing Starlette/httpx deprecation warning. The tests use in-memory Redis fallback for unit isolation; this is not a Redis chaos test. |
| `api\\.venv\\Scripts\\python.exe -m pytest --collect-only -q` | 49 tests collected. |
| `api\\.venv\\Scripts\\python.exe -m alembic check` | `No new upgrade operations detected.` |
| Fresh empty database startup | Applied migrations `0001` through `0009`. Existing database startup also completed and retained its current migration head. |
| `npm audit --audit-level=high` | `found 0 vulnerabilities`. |
| `api\\.venv\\Scripts\\python.exe -m pip_audit -r api/requirements.txt` | An earlier run against the unchanged requirements completed with `No known vulnerabilities found`. The latest invocation stalled without output and was interrupted; rerun in CI or on a network with a responsive advisory service. |
| `api\\.venv\\Scripts\\python.exe api/scripts/run_evals.py` | 3 mock fixtures: precision 1.0, recall 1.0, citation validity 1.0, false-breach rate 0.0. The judgement fixture is fixed and no live model is called. |
| `docker compose config --quiet` | Passed. The effective local API signing key must be supplied; Compose no longer has a weak default. |
| Windows PowerShell parser for launch/service/stop/reset scripts | 0 parse errors. Service logs contained startup output with no `NativeCommandError` wrappers. |
| Tracked-file secret-pattern fallback | 0 private-key, AWS-key, GitHub-token, Stripe-live-key, Resend-key or long environment-secret matches. `gitleaks` is not installed locally. |
| Formatter/backend type checker | No formatter script/configuration or mypy/pyright project configuration is present, so there is no configured formatter or backend typecheck command to run. |

Production smoke requests to `/`, `/login`, `/health`, `/ready`, `/docs`, `/robots.txt` and `/sitemap.xml` returned 200. Home/login responses included CSP, HSTS, `nosniff`, frame and referrer protections. This was a local run; the API was in development mode and `/docs` was therefore available. It is not evidence of a deployed production configuration.

## Journey results

These are the results from checks actually run. “Partial” means relevant code/tests were exercised but the requested persona journey was not completed through the UI.

| Journey/persona | Result | Evidence and limit |
|---|---|---|
| A — Visitor | Partial | Public Chromium flows, theme toggle, contact 429, public axe and 32-route link check passed. Cookie accept/reject/customize/withdraw, full keyboard/mobile/reduced-motion matrix and every page’s metadata were not run. |
| B — Applicant and Platform Owner | Partial | API tests cover pending-organisation restrictions and bootstrap/admin behavior. Signup, email verification, request-more-info, response, approval and rejection were not completed as a browser journey. |
| C — Org Admin and invitee | Partial | Tests cover tenant-scoped invitations, role enforcement, expiry, and redemption workflow. Revoke/regenerate/exhaustion and concurrent single-use redemption were not all driven through the UI. |
| D — Org Admin, sources and rules | Partial | API tests parse PDF/DOCX/TXT, check passage provenance, approval, source versions and suggested rules. No complete browser upload/approval journey was run. |
| E — Creator, skincare campaign | Partial | Scan unit tests cover exact rules, expiry warnings, logos, Hindi banned terms and citations; the mock eval covers discount conflict and unsupported-claim fallback. The requested multi-asset skincare campaign with every expected finding and citation was not run end-to-end. |
| F — Creator and Reviewer | Partial | API test covers idempotent, version-bound review submission/approval behavior. Self-approval, reject-comment/revision/resubmit and post-approval asset edit were not all exercised through UI. |
| G — Proposal extras | Partial | Tests cover Brand Twin evidence/refusal, Hindi exact checks, expiry and feedback suggestions. Evidence Map, prototype labels and platform preview were not comprehensively browser-checked. |
| H — Admin and audit | Partial | Tests cover append-only audit, tenant-scoped audit access, export/deletion and retained audit. Full event ordering, counters, retention edge cases and concurrent behavior were not exhaustively checked. |
| Second organisation | Partial | Invite and audit tests exercise tenant separation. No IDOR matrix was run against every ID-based endpoint or download/export route. |
| Suspended user | Not run | A suspended/stale-token persona journey was not run. |
| Attacker | Partial | Automated tests cover mass assignment, origin rejection, progressive login delay, trusted proxy handling, audit immutability, prompt boundary fixture and citation checks. The full injection/upload/SSRF/concurrency/chaos matrix was not run. |

The complete signup-to-approved-campaign flow using only the UI is **not demonstrated**. Do not present that acceptance item as passed.

## Endpoint and requirement records

- [endpoint-matrix.md](endpoint-matrix.md) inventories 67 API operations, access requirements, tenant scope, route-local throttles and test-family evidence. Test evidence is explicitly marked partial where it is not route-specific.
- `api/openapi.json` now declares the `BrandLensSession` cookie scheme for protected routes and leaves health and public auth flows unauthenticated. `app/lib/api-schema.d.ts` was regenerated. A test checks both cases.
- [requirements-matrix.md](requirements-matrix.md) remains Partial for full responsive coverage, product-route accessibility, complete public metadata/schema validation, network chaos and Lighthouse targets.

## Security posture and residual risks

Implemented and exercised in some form: tenant-aware query helpers, role checks, organization-verification gates, session cookies, origin/Fetch Metadata checks for mutations, Redis-backed rate-limit code, upload magic-byte checks and private storage, append-only audit controls, model-output schema/citation checks, private API proxying, security headers, and loopback-only local Compose ports. The API tests cover selected invite, audit, mass-assignment, request-origin, rate-limit, prompt-boundary and citation cases.

This does not prove every route is IDOR-safe or every role combination correct. Redis-backed production rate limiting and concurrent redemption/approval/scan behavior, reverse-proxy trust in a deployed topology, CSRF under a production browser setup, malicious archive/polyglot/zip-bomb uploads, disk exhaustion, and worker/API/database/Redis chaos were not exhaustively exercised. The development database account still has a fixed local-only credential; it is now reachable through loopback-published ports only. Do not reuse those development credentials in deployment.

No Gitleaks executable was available locally; the tracked-file fallback found no high-confidence credential patterns. CI has a Gitleaks action, but no CI run was recorded here. Lighthouse was not run, so no 95+ score is claimed. Axe ran only on key public pages, not every authenticated route/theme. No real email, AI vendor, external S3, malware scanner or production domain was configured.

## Remaining prototypes and configuration needed

- Vector search uses deterministic lexical-hash vectors, not semantic embeddings. No live LLM provider adapter is included. The mock evaluation figures are not model-quality results.
- Hindi exact checks and platform previews are rule-based prototypes. OCR and malware scanning are optional and depend on configured tools/services.
- Configure LLM and embedding providers/adapters and keys only after selecting a vendor, reviewing the data-processing agreement, and explicitly enabling tenant processing. Configure Resend (or production SMTP) with a verified sender for email delivery.
- Provide public domain/DNS, TLS ingress and sanitized proxy headers; production `APP_SECRET_KEY`, secure cookies, managed Postgres with pgvector, Redis, private object storage, backups and restore verification.
- Complete real-device/browser and screen-reader checks; review Terms/Privacy with counsel; review retention and deletion obligations; sign the AI vendor DPA before sending organisation content to a model.

## Evidence-based score

| Category | Score | Weight | Evidence and limit |
|---|---:|---:|---|
| Functionality and correctness | 6.0/10 | 30% | Core APIs, scan checks and launcher work in tested slices; no completed UI journey or full skincare acceptance run. |
| Security and tenant isolation | 6.0/10 | 25% | Selected authorization/security tests pass and local exposure/OpenAPI gaps were fixed; no complete route-by-route IDOR or chaos audit. |
| UX and accessibility | 6.5/10 | 20% | Public axe, contrast checks, responsive layouts in code and theme E2E pass; product keyboard/axe and device matrix remain unverified. |
| Reliability and testing | 6.5/10 | 15% | Clean start/stop, production build, Postgres migration check and 49 API/6 browser/5 unit tests pass; provider and chaos suites are absent. |
| Maintainability | 7.5/10 | 10% | Current schemas, migrations, lint/typecheck, phase commits and operations docs; formatter/backend typecheck and deployed CI evidence are missing. |

Weighted result: `6.0×0.30 + 6.0×0.25 + 6.5×0.20 + 6.5×0.15 + 7.5×0.10 = 6.325`, reported as **6.3/10**.

**Temporary test-artifact cleanup note:** Filesystem deletion of the two verified `%TEMP%` directories was rejected by the command safety policy. The original repository `.env` and `api/.env` files were never deleted or modified. The temporary directories are `%TEMP%\brandlens-coldstart-20261026` (temporary backups of those local env files) and `%TEMP%\BrandLens-sim-clean-20261026` (the isolated test checkout and its generated env). Remove those directories manually after reviewing them; do not commit their contents.


