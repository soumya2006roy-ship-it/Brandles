# API and development guide

## Local development

Copy `.env.example` to `.env`, install Node dependencies with `npm ci`, create the API environment with `python -m venv api/.venv`, and install `api/requirements.txt`. With Docker available, `docker compose up --build` starts the full local environment and applies migrations. Without Docker, use SQLite-backed API tests and `npm run dev` for the web UI; these do not provide a production API stack.

The API OpenAPI document is `api/openapi.json`; generated TypeScript definitions are `app/lib/api-schema.d.ts`. Regenerate them after schema changes:

```powershell
api\.venv\Scripts\python.exe api\scripts\export_openapi.py
npx openapi-typescript api/openapi.json -o app/lib/api-schema.d.ts
```

The live API schema is at `/api/openapi.json` outside production, and interactive docs are at `/docs` outside production. In production these endpoints are disabled.

## Campaign Health

- `GET /api/v1/orgs/{org_id}/campaigns/health` returns tenant-scoped campaign health summaries and Healthy/Warning/Critical counts.
- `GET /api/v1/orgs/{org_id}/campaigns/{campaign_id}/health` returns one campaign's score, check breakdown, and recommendations.
- Both endpoints require an active session. Organisation members can read only their own approved workspace; a Platform Admin can inspect any active organisation. Non-members receive 404 to avoid exposing whether an organisation exists.
- `Accept-Language: hi` or `Accept-Language: mr` localizes health check messages; unknown languages fall back to English. Scores use only stored dates, channel assets, current scan/finding state, and update age. No budget/performance measurements are inferred.

## Brand Health analytics

- `GET /api/v1/orgs/{org_id}/analytics/brand-health` accepts `start_date`, `end_date`, `campaign_id`, `content_type` (`text`, `image`, `document`), and `severity` (`low`, `medium`, `high`, `critical`). Dates are ISO calendar dates; the maximum range is 731 days.
- Response sections: `summary`, `violations`, `trend`, `review_times`, `confusing_rules`, and `campaigns`. It reads scans, findings, current assets, review records, and append-only resolution events, all tenant-scoped.
- Compliance score is a transparent indicator: open Critical/High/Medium/Low findings carry 25/15/8/3 points; each current asset provides 40 points of capacity, and the score is clamped to 0–100. It is not a legal compliance score or external performance metric.
- Campaign violation rate means the percentage of current campaign assets that have at least one finding in the filtered period. Review turnaround is time from scan creation to resolution or review decision. Median and per-reviewer averages are returned when data exists.
- A rule is shown for review at a dismissal rate of 25% or a repeat rate of 30%. A repeat means a same-rule finding created after an earlier same-rule finding was resolved or dismissed in the selected date range; this indicates a recurring flag, not proof that the rule is wrong or that content was reintroduced.
- `api/scripts/seed_brand_health.py` writes a separately named `[DEMO DATA]` workspace with four campaigns and 60 daily scan dates per campaign (240 scans), mixed finding states and reviewer history. It only uses an existing active account supplied with `--email`, requires `--confirm-demo-data`, refuses `APP_ENV=production`, and skips unchanged on a repeat run. Run from PowerShell at the repository root:

```powershell
api\.venv\Scripts\python.exe api\scripts\seed_brand_health.py --email your-account@example.com --confirm-demo-data
```

- The Brand Health page is `/app/organisations/{org_id}/brand-health`. It supports date, campaign, content type and severity filters, responsive trend/violation/campaign summaries, and CSV export. The trend chart is a labelled inline SVG; no charting dependency was added.

## Tests

```powershell
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
api\.venv\Scripts\python.exe -m pytest -q
api\.venv\Scripts\python.exe api\scripts\run_evals.py
```

The PostgreSQL integration check runs when `TEST_DATABASE_URL` is set to a clean database after `alembic upgrade head`. GitHub Actions provisions a disposable PostgreSQL/pgvector and Redis service for integration checks. The local suite uses SQLite and an in-memory email adapter by default.

## Operational endpoints

- `GET /health`: liveness only; it does not promise dependencies are ready.
- `GET /ready`: checks PostgreSQL and Redis; returns 503 when either is unavailable.
- `GET /metrics`: Prometheus text format for process-local request, job and LLM counters.

Every API response includes `X-Request-ID`; caller IDs are accepted only when they match a conservative character/length allow-list. JSON logs contain the ID, method, path, status and elapsed time. Query strings and request bodies are excluded.
