# API and development guide

## Local development

Copy `.env.example` to `.env`, install Node dependencies with `npm ci`, create the API environment with `python -m venv api/.venv`, and install `api/requirements.txt`. With Docker available, `docker compose up --build` starts the full local environment and applies migrations. Without Docker, use SQLite-backed API tests and `npm run dev` for the web UI; these do not provide a production API stack.

The API OpenAPI document is `api/openapi.json`; generated TypeScript definitions are `app/lib/api-schema.d.ts`. Regenerate them after schema changes:

```powershell
api\.venv\Scripts\python.exe api\scripts\export_openapi.py
npx openapi-typescript api/openapi.json -o app/lib/api-schema.d.ts
```

The live API schema is at `/api/openapi.json` outside production, and interactive docs are at `/docs` outside production. In production these endpoints are disabled.

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
