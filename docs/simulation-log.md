# BrandLens simulation log

## Pass 4 — current checkout regression check (2026-10-27)

### Ran

- `git status --short --branch` — started clean at `425767b` (`origin/main`). Docker was initially unavailable, then became available during this pass (engine 29.9.2).
- `npm run lint` — passed before and after the config-comment cleanup.
- `npm run typecheck` — passed before and after the config-comment cleanup.
- `npm run build` — passed; generated standalone runtime and all configured light/dark contrast pairs passed.
- `npm test` — 5 tests passed.
- `npm run test:e2e` — 6 Chromium tests passed, including public-page axe, account entry points, retired route, theme toggle and contact validation/rate limiting.
- `api\\.venv\\Scripts\\python.exe -m pytest --collect-only -q` — 49 tests collected.
- `api\\.venv\\Scripts\\python.exe -m pytest -q` without PostgreSQL — 48 passed, 1 skipped. After Docker became available, the full suite against a fresh PostgreSQL 17/pgvector container passed: 49 passed, one Starlette/httpx deprecation warning.
- `api\\scripts\\run_evals.py` — 3 fixed fixtures; precision 1.0, recall 1.0, citation validity 1.0, false-breach rate 0.0. This evaluates the deterministic fixtures, not a live model.
- `npm audit --audit-level=high` — 0 vulnerabilities.
- `api\\.venv\\Scripts\\python.exe -m pip_audit -r api\\requirements.txt` — unable to resolve `sentry-sdk<3,>=2.0` from the configured package index; audit is inconclusive.
- Tracked-file credential-pattern fallback — no private-key, common `sk-` token, or Google API-key matches. Gitleaks, formatter and mypy/pyright are not configured/installed; no formatter or backend static type-check command is defined in the repo.
- Created a disposable PostgreSQL 17/pgvector container on port 55433 with no persistent volume. Migrations `0001`–`0009` applied, `alembic check` reported no drift, the migration chain downgraded to base and reapplied successfully, and the audit-trigger integration assertion passed. Removed only the disposable container; existing `hackathon` Postgres/Redis/Mailpit containers and volumes remained healthy and untouched.
- The full Windows launcher cold start and full persona journeys were not repeated in this pass; earlier isolated clean-start evidence remains documented above.

### Findings and fixes

- P3: Next config comment still referred to a “local demo mode” after the demo route was removed. Updated the comment to describe the workspace interface accurately.
- Retest: build, typecheck and lint passed after the comment-only edit.
- No P0/P1 issue was found in the checks completed in this pass. This does not close the previously listed unverified full journeys or adversarial/chaos checks.
- Commit for the initial Pass 4 record and comment cleanup: `1f4fd31` (`docs: record current BrandLens simulation results`). PostgreSQL follow-up results are pending documentation commit.

Date: 2026-10-26. Scope follows the final simulation brief. Existing local `.env` files and Docker volumes are user data; cold-start work uses protected backups and an isolated Compose project.

## Pass 1 — static sweep and cold-start preparation

### Ran

- `npm run lint` — passed.
- `npm run typecheck` — passed.
- `npm run build` — initially failed on Windows with `EPERM` while Next tried to unlink generated output under the OneDrive checkout.
- `api\\.venv\\Scripts\\python.exe -m pytest --collect-only -q` — passed; 48 tests collected.
- `npm audit --audit-level=high` — passed; 0 vulnerabilities.
- `api\\.venv\\Scripts\\python.exe -m pip_audit -r api/requirements.txt` — passed; no known vulnerabilities.
- `docker compose ps -a` — existing project Postgres, Redis and Mailpit are running and healthy. Existing `hackathon_postgres_data` and `hackathon_redis_data` volumes are preserved.
- Static searches for TODO/debug output, unsafe HTML, eval, wildcard CORS, `verify=False`, and public demo routes found no unjustified production matches. A few low-risk style/config findings remain under review.

### Findings and fixes

- P1: the production build was not repeatable in this synced Windows checkout because Next's generated directory could not be unlinked. Added a guarded cleanup script limited to the configured generated build directory and made it run before `next build`.
- Commit: `4779a98` (`fix: make production builds repeatable on Windows`).
- Retest: `npm run build` passed twice; lint and typecheck passed after the change.

### Cold-start status

- Not yet run at the time of this entry. The cold-start will use temporary env-file backups and a unique Compose project name; it will not delete the pre-existing project volumes.

### Remaining pass-1 work

- Run a true first-run setup after removing generated dependencies, build output, logs and local env files; then repeat launch and production mode.
- Continue API, browser, route-contract, accessibility and resilience checks. The complete signup-to-approved-campaign journey and several chaos drills need isolated personas/services and are not yet verified.

## Pass 2 — empty checkout launcher simulation

### Ran

- Created a fresh source export at `%TEMP%\\BrandLens-sim-clean-20261026`; it started without `.env`, `api/.env`, `node_modules`, `api/.venv`, logs, or build output. The original checkout's ignored environment files and data volumes were untouched.
- Ran `start.bat` with a separate Compose project and free test ports. It generated local settings, installed 488 npm packages (0 audit findings), created a Python environment, installed API dependencies, created fresh Postgres/Redis volumes, applied migrations `0001`–`0009`, bootstrapped the platform administrator, and started API, worker and web.
- `/`, `/health`, `/ready`, `/docs`, and Mailpit returned HTTP 200; readiness reported database and Redis healthy.
- Ran `start.bat` a second time; it reported the running app was healthy. Ran `stop.bat`; ports 3000 and 8000 had no listeners. Ran `start.bat prod`; production build completed, standalone web started and stopped cleanly.
- Removed only the isolated simulation project's temporary Docker volumes after the run. Confirmed the original `hackathon_postgres_data` and `hackathon_redis_data` volumes remained present.
- Chromium Playwright: 6 passed, including the public axe checks. `npm run check:links`: 32 routes/assets passed on the production server.

### Findings and fixes

- P2: Windows PowerShell wrapped normal Uvicorn/worker stderr as `NativeCommandError` in logs. The service logger now strips PowerShell's wrapper and preserves original log text. Retest: API, worker and web logs had startup records and no wrapped errors.
- P2: replacing an existing container mapping initially hit a Windows port-rebind conflict. The launch stopped cleanly; the next `start.bat` run succeeded, and all later containers reported healthy. This first-replacement race remains a transient platform limitation.
- P0/P1: none found in the clean-start and public browser smoke subset.

## Pass 3 — contract and local security regression

### Ran

- Full `npm run lint`, `npm run typecheck`, and `npm run build` after source changes — all passed; the contrast script passed configured light/dark token pairs.
- Full API suite with local PostgreSQL via `TEST_DATABASE_URL`: 49 passed, one Starlette/httpx deprecation warning. Runtime was 302.08 seconds in this OneDrive workspace.
- `alembic check` — `No new upgrade operations detected.`
- Production smoke: home/login and API health/readiness/docs returned 200; home/login carried CSP, HSTS and security headers; readiness was healthy.
- npm audit — 0 vulnerabilities. The latest pip-audit invocation stalled without output and was interrupted; an earlier run against the unchanged `api/requirements.txt` completed with `No known vulnerabilities found`.
- `npm run test:e2e` — 6 passed. The 3-case mock evaluation set — precision 1.0, recall 1.0, citation validity 1.0, false-breach rate 0.0.
- `docker compose config --quiet`; Windows PowerShell parsed launch, service, stop and reset scripts without errors.

### Findings and fixes

- P1: Compose published local development services on all interfaces and had a weak fallback signing key. Ports now bind to `127.0.0.1`; Compose requires `APP_SECRET_KEY` instead of supplying a known fallback. Retest recreated the stack using its existing volumes; Postgres, Redis and Mailpit became healthy with loopback bindings.
- P1: the API OpenAPI schema omitted cookie authentication, making protected endpoints appear unauthenticated to generated clients and docs. Added `BrandLensSession` cookie security to protected operations, excluded actual public operations, regenerated `api/openapi.json` and TypeScript declarations, and added a regression test.
- Commit: `897aa4a` (`fix: document API auth and harden local launcher`).
- P0/P1: none remain in the checks actually run. Many acceptance journeys and adversarial cases are still unverified; see the final report.

- P2 follow-up: explicit `rel="noopener noreferrer"` was added to the two external organisation links flagged by the static sweep; `npm run lint`, `npm run typecheck`, and `npm run build` passed afterward. Commit: `56dceec`.

## Final status note

- Post-link-fix `npm run lint`, `npm run typecheck`, and `npm run build` all passed; `npm test` passed 5 tests and the final Chromium run passed all 6 tests.
- Targeted tracked-file credential patterns found no private keys or recognized provider tokens. Gitleaks is not installed locally; CI configuration was not executed.
- The generated test checkout and the temporary env backups are under `%TEMP%`, outside the repository. Cleanup was blocked by the command safety policy even after checking their exact resolved paths. They contain generated test environment files / copies of the original ignored environment files; the original repository env files and Docker data volumes were preserved. See the final report for the exact temp paths to remove manually.
