# Launch verification

Date: 2026-10-26. This report records checks that ran in the available Windows environment. Docker Desktop is not installed, so the complete launcher flow could not run.

## Launcher result

Ran `cmd.exe /c start.bat` and `npm run dev:all`. Node v24.12.0, npm 11.6.2 and Python 3.13.14 passed prerequisite checks. Both entry points stopped with the Docker Desktop and Compose install instructions before creating environments, installing packages, starting data services or launching application processes. No product service ports remained open. This verifies fail-closed behavior and the Windows Node dispatcher only.

The clean-state run, second-start idempotency run, stop/reset checks, missing-port conflict, container startup, migrations through the launcher, and production mode remain unverified. I did not remove the existing dependency environments or any `.env` files when Docker was unavailable. The macOS/Linux shell launcher was not executable in this Windows environment because WSL/Git Bash is unavailable.

## Route and browser checks

| Check | Result |
| --- | --- |
| `npm run lint` | Passed. |
| `npm run typecheck` | Passed. |
| `npm run build` | Passed; route output includes `/signup`, `/org/create`, `/join`; no retired route is in the build. Contrast checks passed in light and dark themes. |
| `npm test` | Passed: 5 tests. |
| `npm run test:e2e` | Passed: 6 Chromium tests, covering public pages, account forms and aliases, signed-out product redirects, the retired route response, theme behavior, contact throttling and public-page axe checks. These are not a signup-to-reviewer-approval journey. |
| `npm run check:links` | Passed against the running Next development server: 32 internal routes and required metadata assets returned below HTTP 400; the retired path returned 404 and was absent from the sitemap. |
| `git diff --check` | Passed. |

## API checks

`api\.venv\Scripts\python.exe -m pytest -q` completed with **47 passed, 1 skipped, 1 warning** in 341 seconds. The skipped case needs PostgreSQL; the warning is the existing Starlette/httpx test-client deprecation.

For an HTTP smoke without Docker, Uvicorn was run with a temporary in-memory SQLite URL and local-only secret. Real requests returned:

```text
GET /health            200  {"status":"ok"}
GET /docs              200
GET /api/openapi.json  200  title: BrandLens API
```

This temporary setup does not verify Postgres, Redis readiness, email delivery, signup verification, organization verification, uploads, scans, reviews, or audit behavior over a live service stack.

## Removal scan

The repository scan finds the retired path only in its explicit 404/sitemap assertions in `e2e/public-pages.spec.ts` and `scripts/check-site-links.mjs`. These are intentional checks required to prove the route is gone. No public navigation, page copy, sitemap, runtime API route, or provider points to it.
