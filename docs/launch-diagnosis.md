# Launcher diagnosis

Date: 2026-10-26. This diagnosis was reproduced from the repository root on Windows.

## Launcher and service inventory

| Entry point | Working directory | What it runs | Ports / mode |
| --- | --- | --- | --- |
| `start-brandlens.bat` | Correctly switches to `%~dp0` with `cd /d` | If Docker CLI and engine are available, starts `docker compose up --build` in a persistent console and opens port 3000. If Docker is unavailable, it installs root npm dependencies if absent and starts only `npm run dev` in a persistent console. | Full branch: Compose development stack (web 3000, API 8000, PostgreSQL 5432, Redis 6379, MinIO 9000/9001, Mailpit 8025). Fallback: Next development web only on 3000. |
| `npm run dev` | Package root | Next.js development server. | 3000, frontend only. |
| `npm run dev:all` | Package root | `docker compose up --build` for the development stack. | Ports listed above. |
| `npm run build` / `npm run start` | Package root | Production build and generated standalone Next server. | Build only / web server 3000; no API or dependencies. |
| `docker-compose.yml` | Compose project root | Next web, FastAPI, worker, PostgreSQL/pgvector, Redis, MinIO/init, Mailpit. API command runs `alembic upgrade head` before Uvicorn. | Full local stack; dev settings include mock LLM and lexical-hash embeddings. |
| `compose.production.yaml` | Compose project root | One-shot migrations, API, worker and web, expecting externally supplied DB, Redis, object storage and secrets. | Web configurable at 3000; API is internal. Production mode. |
| Other `.bat`, `.cmd`, `.ps1`, `.sh`, Makefile, Procfile | Repository search found none. | — | — |
| Other `package.json` files | Repository search found only the root `package.json` outside dependency/build folders. | Scripts are `dev`, `dev:all`, `build`, `start`, lint/typecheck/test, contrast and OpenAPI/type generation. | — |

## Root cause and checks

**Confirmed root cause:** when Docker is absent or its engine is stopped, the batch file explicitly falls back to the frontend-only `npm run dev` path and prints that the organisation workspace needs Docker. The product UI routes are present, but their `/api/product/*` proxy targets `BRANDLENS_BACKEND_URL` (default `http://127.0.0.1:8000`) and no API is launched by that fallback. Therefore login and product screens can render while their real API requests fail. The fallback does not start the worker, database, Redis or storage.

Reproduction:

- Before launch, Docker was not installed (`docker` command not found) and ports 3000, 8000, 5432, 6379, 9000, 9001 and 8025 had no listeners.
- Ran `cmd.exe /c start-brandlens.bat` in a terminal. It printed `Docker is unavailable. Starting the public marketing site only.` and `The organisation workspace needs Docker Desktop and the full product stack.`
- The launched Next dev server returned HTTP 200 at `http://127.0.0.1:3000/` with title “Catch campaign conflicts before approval”. No API or backing service ports opened. `http://127.0.0.1:8000/health` was unreachable.
- The running frontend was the Next development app, not a static export or a stale build. The batch file uses the correct repository directory. `next.config.ts` sets `output: "standalone"`, not export, and has no rewrite to the removed marketing page. Product routes exist in the route tree. `/app` requires authentication and redirects to login; it does not redirect to the public campaign page.
- The public root and navigation did prominently link to the sample workspace. The sample page used an actual sample API endpoint backed by an opt-in seed script, not an in-memory product API. In development Compose, the *judgement provider* is explicitly a mock that returns insufficient evidence; this is a known AI limitation and is not a frontend route fallback.
- No port conflict was present before launch. Missing real backend services were the direct reason product requests were unavailable. Database migration status and API crash behavior could not be tested because Docker was unavailable.

## Product API coverage and persistence

The frontend funnels authenticated product requests through `app/lib/api-client.ts` and `app/api/product/[...path]/route.ts` to FastAPI under `/api/v1`. These are real endpoint groups backed by SQLAlchemy models and Alembic migrations, not a front-end mock layer:

| UI area / request family | FastAPI endpoint group | Persistence and migration evidence |
| --- | --- | --- |
| Registration, login/logout, verification, password reset, current user and sessions | `/auth/*` | `users`, `auth_tokens`, `sessions`; migration chain `0001` onward. |
| Organisation onboarding, member/invite actions, audit, platform verification | `/orgs`, `/orgs/{id}/*`, `/invites/*`, `/platform/verifications/*` | `organizations`, `memberships`, `invites`, `verification_decisions`, `audit_events`; migrations `0001`, `0005`, `0007` and later. |
| Workspace settings, notification preferences, retention, export/deletion | `/orgs/{id}/settings`, `/notification-preferences`, `/retention-settings`, `/data-export`, `/data-deletion` | `organizations`, `memberships`, `notifications`, `audit_events`; migrations through `0008`. |
| Approved sources, passage search/download/approval, rules | `/orgs/{id}/sources/*`, `/passages/*`, `/rules/*` | `brand_guideline_sources`, `source_passages`, `rules`; migration `0002` and later. |
| Campaigns, assets/download, scans/cancel/resume, findings/decisions/clarifications, facts and reviews | `/orgs/{id}/campaigns/*`, `/findings`, `/reviews/*` | `campaigns`, `assets`, `scans`, `findings`, `extracted_facts`, `reviews`; migrations `0003`–`0005` and later. |
| Brand Twin, notifications, suggested guideline updates | `/orgs/{id}/brand-twin/ask`, `/notifications/*`, `/guideline-update-suggestions/*` | `source_passages`, `notifications`, `guideline_update_suggestions`; migrations `0005`–`0006` and later. |
| Public seeded workspace | `/sample-workspace` | Special `organizations.is_sample` flag and related sample records introduced by migration `0006`; seed is `api/scripts/seed_sample_workspace.py`. This surface is removed in Phase 2. |

The product route calls correspond to implemented API routes and models in the repository. This static inventory does not prove runtime correctness; only the full-stack tests against live services can do that. Current development Compose config supplies a mock judgement client and deterministic lexical-hash embeddings, so it does not provide real model judgement or semantic vectors. Optional OCR and malware scanning require configuration.

## Demo / sample implementation inventory

Phase 2 removes product-facing sample/simulation code and wording. Keep only explicitly test-only fixtures/mocks and the separate labeled evaluation corpus where appropriate. Remove or replace the following repository entries:

| Surface | Action |
| --- | --- |
| `/demo` route, loading, page, sample client, old browser simulation and its loader/Open Graph image | REMOVE |
| Public API `GET /api/v1/sample-workspace`, router, response schema, sample package and sample seed script | REMOVE |
| `Organization.is_sample`, mutation/deletion restrictions that only protected the sample, and the migration's sample-only schema | REMOVE through a forward migration; preserve historical migrations and their checksums. |
| Home/header/mobile/related links, feature copy, roadmap, contact FAQ, breadcrumbs, metadata, sitemap and tracking event types | REPLACE with real account, invite and contact entry points; retain proposal-accurate product descriptions and prototype disclosures. |
| README, decisions, audit/final docs, OpenAPI and generated frontend API schema | UPDATE and regenerate; remove user-facing claims about the sample workspace. |
| Pytest mock LLM and labeled evaluation fixtures under test/evaluation paths | KEEP when they are imported only by tests/evaluation, not as a public runtime workflow. |

