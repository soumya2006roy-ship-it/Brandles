# Launch verification

Date: 2026-10-26. This run used Docker Desktop 4.97.0 / Engine 29.9.2 on Windows, Node 24.12.0, npm 11.6.2, Python 3.13.14, and the repository checkout under OneDrive.

## Full-stack development launch

Docker Desktop was installed in the current user's profile and its CLI was not on the shell PATH. The Windows launcher now checks Docker Desktop's standard per-user `resources/bin` location. The local database, Redis and Mailpit ports (5432, 6379, 8025 and 1025) were already occupied by Docker Desktop/WSL relay listeners, so this machine's ignored `.env` and `api/.env` use host ports 55432, 16379, 18025 and 11025. The project defaults remain the conventional ports; other users do not need these overrides unless their ports are occupied.

The first Docker pull exposed that the configured MinIO Docker Hub image is no longer available. Local development now uses the existing private local-file storage implementation instead of depending on MinIO. Production S3-compatible storage configuration remains available. No Docker volumes were deleted during this verification.

`start.bat`'s PowerShell target completed successfully after configuration: the PostgreSQL/pgvector, Redis and Mailpit containers became healthy; Alembic applied migrations through `0009_remove_public_workspace_marker`; the local platform admin bootstrap ran; and the API, worker and web processes started. A second launch detected the healthy existing app and returned without duplicating processes.

The following HTTP checks returned 200 while the app was running:

```text
GET /health                 200
GET /ready                  200  {"status":"ready","checks":{"database":true,"redis":true}}
GET /                       200
GET /docs                   200
GET Mailpit inbox           200
```

`stop.bat` stopped the application processes. `stop.bat containers` stopped the database, Redis and Mailpit containers; all project volumes remained present. The app and configured host service ports had no listeners after stopping. The destructive `reset-dev.bat` flow was intentionally not run; it requires deleting local database/upload volumes.

## Production mode

At the time of this earlier run, `npm run build` failed with `EPERM` unlinking generated output in this OneDrive-synced checkout. This was fixed later by a guarded cleanup of only `.next-brandlens-build`; the current result is recorded in [final-simulation-report.md](final-simulation-report.md).

## Checks

| Check | Result |
| --- | --- |
| `docker compose config --quiet` | Passed. |
| Windows PowerShell 5.1 parser for launch, stop and reset scripts | Passed. |
| `npm run lint` | Passed. |
| `npm run typecheck` | Passed. |
| `npm test` | Passed: 5 tests. |
| `npm run test:e2e` | Passed: 6 Chromium tests, including contact rate limiting and axe checks on key public pages. |
| `npm run check:links` | Passed: 32 routes plus required metadata assets. |
| `api\.venv\Scripts\python.exe -m pytest -q` with `TEST_DATABASE_URL=postgresql+psycopg://brandlens:brandlens@localhost:55432/brandlens` | Passed: 48 tests, including the real-PostgreSQL migration/audit integration check; one existing Starlette/httpx deprecation warning. Unit tests isolate Redis rate-limit keys from the local app. |
| `api\.venv\Scripts\python.exe api/scripts/run_evals.py` | Passed: precision 1.0, recall 1.0, citation validity 1.0, false-breach rate 0.0 on 3 fixtures. Evaluation judgement uses a fixed insufficient-evidence fixture; it does not call a live model. |
| `git diff --check` | Passed. |

The tests do not demonstrate the complete signup-to-approved-campaign acceptance journey, a live LLM, external email delivery, malware/OCR configuration, production S3 deployment, or Lighthouse results.
