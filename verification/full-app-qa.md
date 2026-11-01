# BrandLens full app QA — 1 Nov 2026

## Summary

QA ran on branch `fix/full-app-qa`. The hosted signup 500 shown in the earlier Render log was caused by the deployed PostgreSQL schema missing `users.recovery_question` (and its matching answer hash column) while the current API queried both columns. Migration `0011_account_recovery_questions` adds the nullable columns and is safe for databases where the columns already exist. Existing accounts retain `NULL` recovery fields and can continue using email password reset. The repository startup command already runs `alembic upgrade head` before starting Uvicorn.

This local session did not connect to or modify the hosted database. The signup code path passed its SQLite-backed API tests. A real PostgreSQL migration run could not be completed because Docker Desktop's Linux engine is unavailable and `TEST_DATABASE_URL` is unset.

## Features added 30–31 October

- **Brand Health analytics** (`44a0ab1`, `8486880`): tenant-scoped analytics API at `/api/v1/orgs/{org_id}/analytics/brand-health`, dashboard at `/app/organisations/{organizationId}/brand-health`, accessible chart updates. Exercised by `test_brand_health_analytics.py` in the API suite.
- **Visual Compliance prototype** (`eaa1051`): visual upload/check flow at `/app/organisations/{organizationId}/visual-compliance`, asset upload and scan endpoints, finding decisions, migration `0010_expand_finding_status`, generated image fixtures and tests. API tests passed. This remains a deterministic prototype: colour/palette and perceptual logo checks are heuristics; OCR is optional; no font recognition or live LLM behavior is claimed.
- **Recovery-question password reset** (`b60563e`): signup stores a recovery question and a hashed answer; `/api/v1/auth/password-reset/recovery-question` verifies case-insensitively, changes the password, and revokes sessions. Migration `0011_account_recovery_questions` is additive and idempotent for existing columns. Unit tests cover correct/wrong answers and session revocation.
- **Supporting verification/accessibility work** (`f0a0051`, `62d9325`, `9ef7cf2`): chart accessibility and browser verification records.

## Project map

- **Stack:** Next.js 16.4.3 App Router, React 19, TypeScript, Tailwind 4; FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/pgvector, Redis; Resend and Playwright/Vitest.
- **Web pages:** public marketing routes `/`, `/problem`, `/how-it-works`, `/campaign-consistency-graph`, `/features`, `/roles`, `/security`, `/roadmap`, `/contact`, `/privacy`, `/cookies`; auth routes `/login`, `/sign-up`, `/signup`, `/forgot-password`, `/reset-password`, `/reset-with-question`; workspace routes `/app`, `/app/invite`, `/app/organisations/new`, `/app/organisations/[organizationId]` and its audit, brand-health, campaign-health, campaigns, findings, reviews, rules, sources and visual-compliance pages, plus `/app/admin/verifications`, `/app/account/sessions`, and `/app/security`.
- **API groups:** health/metrics; auth register/login/logout/me/password-reset/recovery/sessions; organization, membership, invite and platform verification; campaign, analytics, campaign health, assets, visual-check, scans, facts, findings, review queue/decisions, notifications, guideline suggestions and Brand Twin; source/passages/download/approval/rules; organization settings, notification/retention settings, export/deletion; private file download. API routes are mounted under `/api/v1`; the web proxy exposes them under `/api/product`.
- **ORM models:** `User`, `PlatformAdmin`, `Organization`, `Membership`, `Invite`, `AuthToken`, `SessionRecord`, `VerificationDecision`, `AuditEvent`, `BrandGuidelineSource`, `SourcePassage`, `Rule`, `Campaign`, `Asset`, `ExtractedFact`, `Scan`, `Finding`, `Review`, `GuidelineUpdateSuggestion`, `Notification`.
- **`.env.example` names:** `NEXT_PUBLIC_SITE_URL`, `BRANDLENS_BACKEND_URL`, `WEB_PORT`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, `FRONTEND_ORIGIN`, `APP_ENV`, `APP_SECRET_KEY`, `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_NAME`, `SESSION_TTL_HOURS`, `DATABASE_URL`, `POSTGRES_PORT`, `REDIS_URL`, `REDIS_PORT`, `MAILPIT_UI_PORT`, `MAILPIT_SMTP_PORT`, `RATE_LIMIT_MULTIPLIER`, `TRUSTED_PROXY_CIDRS`, `EMAIL_PROVIDER`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `CONTACT_FROM_EMAIL`, `CONTACT_TO_EMAIL`, `CONTACT_REPLY_TO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `FILE_STORAGE_DRIVER`, `LOCAL_STORAGE_PATH`, `MALWARE_SCANNER_HOST`, `MALWARE_SCANNER_PORT`, `MALWARE_SCAN_TIMEOUT_SECONDS`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION`, `S3_SIGNED_URL_TTL_SECONDS`, `ALLOW_WORKSPACE_LLM`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `SCAN_MAX_ASSETS`, `SCAN_MAX_CLAIMS`, `SCAN_TIMEOUT_SECONDS`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`, `EMBEDDING_DIMENSIONS`, `OCR_PROVIDER`, `TESSERACT_COMMAND`, `TESSERACT_TIMEOUT_SECONDS`, `VISUAL_CONFIDENCE_THRESHOLD`, `VERIFICATION_TOKEN_TTL_MINUTES`, `PASSWORD_RESET_TTL_MINUTES`, `TEST_DATABASE_URL`. Values are deliberately omitted.

## Fixes made

1. **Validation and duplicate registration statuses.** Request schema errors now return HTTP 400; duplicate signup returns HTTP 409 with a clear message; authentication failures remain 401. Exact request validation errors omit submitted values. This follows the requested status behavior. A 409 does reveal that an email is registered; keep that tradeoff in mind if account enumeration becomes a concern.
2. **Server-side exception detail.** The API's unhandled-request middleware now uses `logger.exception` with request ID, method, path and status, so the traceback is available without logging request bodies. Readiness DB/Redis failures, password reset email failures, optional OCR/LLM failures, scan queue/execution failures, document parsing failures, and Next server proxy/session/contact failures now log exception objects. User-facing error responses remain generic where appropriate.
3. **Deterministic browser tests without Redis.** Playwright's local web server now sets `REDIS_URL` to an empty string, selecting the app's in-memory local rate-limit fallback instead of retrying an unavailable Redis service. This change is limited to the E2E server configuration.
4. **Signup regression coverage.** Added API coverage for duplicate email, invalid email, weak password, missing fields, Unicode names, and recovery-answer hashing. Added a Playwright test for the signup request fields and password show/hide toggle.
5. **Link-check route list.** Removed the obsolete `/verify-email` probe; the current product intentionally has no email-verification page or endpoint.

Representative diff:

```diff
- return {"message": "If this address can be registered, the account will be ready to sign in."}
+ raise HTTPException(status_code=409, detail="An account with this email already exists.")

- log_json(logger, "request_failed", ..., status_code=500)
+ logger.exception("Unhandled API request failure", extra={...})
```

## Test results

| Test / area | Before fix | Final result |
|---|---|---|
| Hosted signup root cause | Render log showed `column users.recovery_question does not exist`; hosted DB was not directly queried in this QA run | Migration `0011` already provides the fix; local registration and recovery API tests pass. Production migration still needs to be confirmed in Render logs. |
| Duplicate/invalid signup | Code returned generic HTTP 201 for duplicate and FastAPI schema errors used 422 | PASS: test verifies duplicate 409, invalid/weak/missing input 400, Unicode name accepted, recovery answer hashed. |
| E2E browser suite | First baseline run: 5 passed, contact rate-limit test timed out while Redis was unavailable | PASS: `npm run test:e2e` → 7 passed. New signup/password-visibility test included. Node emitted inherited `NO_COLOR`/`FORCE_COLOR` warnings, not browser-console errors. |
| API suite | Existing recovery flow passed; after status change one old assertion expected 422 | PASS: `python -m pytest -q` → 63 passed, 1 skipped. Updated the mass-assignment test to expect requested 400. Starlette emitted an `httpx` deprecation warning. |
| Frontend unit tests | Not run before code changes in this QA session | PASS: `npm test` → 3 files, 8 tests passed. |
| Lint / typecheck / build | Not run before code changes in this QA session | PASS: `npm run lint`, `npm run typecheck`, `npm run build`; production build and light/dark contrast checks completed. |
| Link checker | Initially failed because its hard-coded `/verify-email` route returned 404; without a server, all checks initially failed to connect | PASS after removing stale path and starting local Next dev server: 32 routes and required metadata assets returned below 400. |
| Campaign health simulation | Not run before | PASS: `npm run simulate:health` → 15 non-persistent scenarios, expected 3 healthy and 3 critical. |
| PostgreSQL migration/append-only integration | Not available in this environment | SKIPPED: `TEST_DATABASE_URL` is not configured; Docker cannot connect to `dockerDesktopLinuxEngine`. |
| Protected workspace UI, hosted Redis, real email, external AI/OCR | Not exercised against live services | NOT RUN: requires working infrastructure/provider configuration. Existing API unit tests cover tenant checks, analytics, campaign health, scans, visual compliance and security behavior on in-memory SQLite. |

Commands to reproduce from the repo root (API tests from `api/`):

```powershell
npm run lint
npm run typecheck
npm run build
npm test
npm run test:e2e
npm run check:links   # start `npm run dev -- --hostname 127.0.0.1` first
npm run simulate:health
Set-Location api
.\.venv\Scripts\python.exe -m pytest -q
```

To run the skipped real PostgreSQL checks, configure `TEST_DATABASE_URL` to a **separate disposable test database** and run `.\.venv\Scripts\python.exe -m pytest -q tests/test_postgres_integration.py` from `api/`. Do not point it at production or the user's hosted database.

## Remaining risks and next steps

- Confirm Render's latest deployment ran `alembic upgrade head` and reached `0011_account_recovery_questions`; re-test signup once against the hosted site. No hosted account or database was changed in this work.
- Run the skipped PostgreSQL migration/integration test on an isolated disposable DB, including upgrade from the previous migration head with existing user rows.
- Full authenticated browser CRUD and true mobile/tablet workspace flows were not simulated here. E2E covers public pages, auth entry points, signup, theme toggle, contact validation/rate-limit behavior and public-page axe checks; API integration tests use in-memory SQLite.
- The API test suite reports a Starlette/httpx deprecation warning. The Playwright runner reports inherited `NO_COLOR`/`FORCE_COLOR` warnings. Neither failed the checks.
- Visual compliance remains a prototype, as described above; validate OCR-backed disclaimers only after configuring OCR and using a test image corpus.
