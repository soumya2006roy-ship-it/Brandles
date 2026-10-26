# Launcher diagnosis

Date: 2026-10-26. This diagnosis was reproduced from the repository root on Windows.

## Launcher inventory

| Entry point | Working directory | What it runs | Ports / mode |
| --- | --- | --- | --- |
| `start-brandlens.bat` (before Phase 3 repair) | Correctly switches to `%~dp0` using `cd /d` | With Docker available, started `docker compose up --build`. Without Docker, explicitly started only `npm run dev`. | Full development stack: web 3000, API 8000, PostgreSQL 5432, Redis 6379, MinIO 9000/9001, Mailpit 8025. Fallback: Next development web only on 3000. |
| `start.bat` | Switches to `%~dp0` using `cd /d` and calls the PowerShell setup orchestrator | Checks Node/npm, Python, Docker/Compose and ports; generates local secrets once, prepares dependencies, starts data services, waits for health, migrates and bootstraps the first local platform administrator, then opens named API/worker/web windows. | Dev by default; `start.bat prod` rebuilds the web app and runs Uvicorn without reload. |
| `start-brandlens.bat` | Compatibility entry point that calls `start.bat` | Forwards arguments and returns the launcher's exit code. | Same as `start.bat`. |
| `start.sh` / `npm run dev:all` | Repository root on macOS/Linux, or cross-platform Node dispatcher | Runs the equivalent environment setup, data-service startup, migration/bootstrap and health checks; writes service logs and PIDs under `logs/`. | Dev by default; optional `prod` mode. |
| `npm run dev` | Package root | Next.js development server only. | Port 3000. |
| `npm run dev:all` | Package root | Starts the platform-specific full launcher. | API, worker and web processes plus PostgreSQL/pgvector, Redis and Mailpit; uploads use a private Docker volume. |
| `npm run build` / `npm run start` | Package root | Next standalone production build/server. | Web only on port 3000; these scripts do not start API or dependencies. |
| `docker-compose.yml` | Compose project root | Next web, FastAPI, worker, PostgreSQL/pgvector, Redis, Mailpit, and a private upload volume. API command runs `alembic upgrade head` before Uvicorn. | Full development stack. The model provider is unconfigured; retrieval vectors are deterministic lexical-hash vectors. |
| `compose.production.yaml` | Compose project root | One-shot migrations, API, worker and web, expecting externally supplied DB, Redis, object storage and secrets. | Web configurable at 3000; API internal. Production mode. |
| `stop.bat` / `stop.sh` | Repository root | Stops processes whose launcher PID and command line match BrandLens service runners; optional flag stops data containers. | Application processes; optionally local containers. |
| `reset-dev.bat` | Repository root | Requires exact typed confirmation, then removes local Compose volumes, development uploads and build/log output. Keeps env files and installed dependencies. | Destructive to local development data only. |
| Other `package.json` files | Repository search found only the root package manifest outside dependencies/build output. | Scripts include full-stack `dev:all`, build, start, lint/typecheck/test, contrast, link checking and OpenAPI/type generation. | — |

## Root cause and reproduction

**Confirmed root cause:** before repair, if Docker was absent or its engine was stopped, the Windows launcher printed that the organisation workspace required Docker and then started only the web app. Product routes rendered, but `/api/product/*` requests target `BRANDLENS_BACKEND_URL` (default `http://127.0.0.1:8000`). No API, worker, database, Redis, object storage or mail service was launched by that branch, so sign-in and workspace data requests could not work. Phase 3 removes this misleading partial-launch behavior.

- Before launch, Docker was not installed (`docker` command not found) and ports 3000, 8000, 5432, 6379, 9000, 9001 and 8025 had no listeners.
- Ran `cmd.exe /c start-brandlens.bat` in a terminal. It printed `Docker is unavailable. Starting the public marketing site only.` and `The organisation workspace needs Docker Desktop and the full product stack.`
- The launched Next development server returned HTTP 200 at `http://127.0.0.1:3000/`. No API or backing-service ports opened. `http://127.0.0.1:8000/health` was unreachable.
- The batch file used the correct repository directory. `next.config.ts` specifies standalone output, not a static export. Root does not redirect to a fictional workspace, and product routes exist in the build route tree. `/app` requires authentication and redirects to login; it does not redirect to a public example page.
- The root page and navigation linked prominently to an unauthenticated campaign example. That former route used a dedicated API endpoint and optional database seed, rather than in-memory product API data. Phase 2 removes those public surfaces.
- There was no port conflict before launch. Missing services were the direct cause of unavailable product requests. Database migration status and API startup could not be checked because Docker is not installed.

## Launcher implementation and verification

The current launch flow validates Node/npm, Python, Docker/Compose, and service ports; creates local secrets once; prepares npm and Python dependencies when their lock/config files change; starts the database, Redis and Mailpit from Compose; waits for PostgreSQL and Redis; runs migrations and idempotent local platform-admin bootstrap; then starts API, worker and web in separate named Windows windows with logs. Local uploaded files use a private Docker volume; production storage remains S3-compatible. It gates success on API `/health` and the web root. `start.bat prod` rebuilds before starting production-mode Next and Uvicorn without reload. `start-brandlens.bat` forwards to this entry point. On macOS/Linux `bash start.sh` and `npm run dev:all` use the equivalent shell flow.

The earlier full-stack launcher was executed in this environment and reported that Docker CLI was unavailable before starting any service. The new launcher flow cannot pass its Docker prerequisite here; its full startup, migrations, service health, browser journey and stop/reset behavior remain unverified until Docker Desktop is available. The diagnosis also found that the product API routes were already implemented; the new work adds canonical route aliases and a server-side session check on product routes.

## Product API and persistence inventory

Authenticated product requests go through `app/lib/api-client.ts` and `app/api/product/[...path]/route.ts` to FastAPI under `/api/v1`. These are server endpoints backed by SQLAlchemy models and Alembic migrations:

| UI area / request family | FastAPI endpoint group | Persistence and migration evidence |
| --- | --- | --- |
| Registration, login/logout, verification, password reset, current user and sessions | `/auth/*` | `users`, `auth_tokens`, `sessions`; migrations `0001` and later. |
| Organisation onboarding, members/invites, audit, platform verification | `/orgs`, `/orgs/{id}/*`, `/invites/*`, `/platform/verifications/*` | `organizations`, `memberships`, `invites`, `verification_decisions`, `audit_events`; migrations `0001`, `0005`, `0007` and later. |
| Workspace settings, notification preferences, retention, export/deletion | `/orgs/{id}/settings`, `/notification-preferences`, `/retention-settings`, `/data-export`, `/data-deletion` | `organizations`, `memberships`, `notifications`, `audit_events`; migrations through `0008`. |
| Approved sources, passages/download/approval, rules | `/orgs/{id}/sources/*`, `/passages/*`, `/rules/*` | `brand_guideline_sources`, `source_passages`, `rules`; migration `0002` and later. |
| Campaigns, assets/download, scans/cancel/resume, findings/decisions/clarifications, facts and reviews | `/orgs/{id}/campaigns/*`, `/findings`, `/reviews/*` | `campaigns`, `assets`, `scans`, `findings`, `extracted_facts`, `reviews`; migrations `0003`–`0005` and later. |
| Brand Twin, notifications, suggested guideline updates | `/orgs/{id}/brand-twin/ask`, `/notifications/*`, `/guideline-update-suggestions/*` | `source_passages`, `notifications`, `guideline_update_suggestions`; migrations `0005`–`0006` and later. |
| Retired public endpoint | `/api/v1/sample-workspace` | Previously read records marked by `organizations.is_sample`, added by historical migration `0006`; API and seed script removed. Migration `0009` tombstones those organizations and drops the marker. |

This is a static mapping. It does not prove that endpoints work against live services. No LLM provider adapter is included; unavailable judgement requires human verification. Lexical-hash vectors are not semantic embeddings. OCR and malware scanning require configuration.

## Phase 2 removal inventory

| Surface | Disposition |
| --- | --- |
| Unauthenticated campaign-example route, loading state, UI, browser state and route-specific Open Graph image | Removed. |
| Public API endpoint, router, schema, package and database seed script | Removed. |
| `Organization.is_sample` and deletion restrictions that only protected that record | Removed through a forward migration. Historical migration files remain unchanged to preserve upgrade history. |
| Home/header/related links, capability copy, roadmap, contact FAQ, breadcrumbs, metadata, sitemap and tracking event types | Replaced with organisation creation, login, invite redemption and contact entry points. |
| README, decisions, audit docs, API schema and generated frontend contracts | Updated or regenerated to match current routes and provider limits. |
| Labeled evaluation cases and deterministic judgement fixture | Kept only for evaluation; not registered as runtime providers. |

