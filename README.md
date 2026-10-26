# BrandLens

BrandLens is an editorial website and an organisation workspace for the source-based brand governance concept described in [`docs/brandlens-proposal.md`](docs/brandlens-proposal.md). Proposal language is the source of truth. The Hindi checker and platform previews remain simple rule-based prototypes.

## Local setup

Requirements: Node.js 20.9 or newer, npm, Python 3.12+, and Docker Desktop with Compose. From the repository root:

```powershell
npm install
Copy-Item .env.example .env.local
Copy-Item .env.example api/.env
npm run dev:all
```

`dev:all` starts Next.js, FastAPI, PostgreSQL with pgvector, Redis, MinIO, a background worker, and Mailpit. Visit `http://localhost:3000`; local email is captured at `http://localhost:8025`. The compose stack uses development-only credentials from `.env.example`. Change them before exposing any service outside localhost.

On Windows, `start-brandlens.bat` opens the full stack when Docker Desktop is running; without Docker, it starts the public marketing site only.

### Sample workspace

`/demo` reads the fictional skincare workspace from the public, read-only `GET /api/v1/sample-workspace` endpoint. After starting the API and applying migrations, seed the sample with:

```powershell
Set-Location api
.venv\Scripts\python.exe scripts\seed_sample_workspace.py
```

The seed command is idempotent. It creates a dedicated sample organization and campaign scan, and refuses to expose regular customer workspaces through the public route. The sample is unavailable until this command has run in the deployment database.

To run only the marketing site, use `npm run dev`; account and organisation features require the API and database. To run the API outside Docker on Windows, create and activate a venv, install the requirements, then run Alembic and Uvicorn:

```powershell
py -3.12 -m venv api/.venv
api/.venv/Scripts/Activate.ps1
pip install -r api/requirements.txt
Copy-Item .env.example api/.env
Set-Location api
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The API docs are available at `http://localhost:8000/docs`. `npm run api:types` exports the FastAPI OpenAPI schema and regenerates TypeScript API types; run it from a shell where the Python environment is active.

### Platform administrator

Platform administrator status is granted only by a trusted operator with local database access. Register the intended account, verify its email using the local Mailpit message, then run:

```powershell
Set-Location api
python -m app.cli promote-platform-admin verified.person@example.com
```

The same CLI supports `revoke-platform-admin`. The verification dashboard is at `/app/admin/verifications` after logging in as that account. The backend checks the database role on every request; an email address or client-side setting cannot grant administrator access.

## Environment variables

`.env.example` lists every supported setting. Copy it to `.env.local` for Next.js and to `api/.env` for direct API runs. Docker Compose reads `.env` at the repository root (copy `.env.example` there when using Compose). Never commit real keys. `APP_SECRET_KEY`, Resend, storage credentials, and the canonical site URL must be configured for deployment.

| Variable group | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL`, `BRANDLENS_BACKEND_URL`, `FRONTEND_ORIGIN` | Canonical metadata origin and private Next-to-FastAPI routing |
| `APP_ENV`, `APP_SECRET_KEY`, `SESSION_*` | Runtime mode, signing secret, and secure session cookie settings |
| `DATABASE_URL`, `REDIS_URL` | PostgreSQL/pgvector and shared rate limits/job queue |
| `EMAIL_PROVIDER`, `RESEND_*`, `SMTP_*` | Verification, reset, invite, and contact messages; use SMTP/Mailpit locally or Resend for deployment |
| `CONTACT_*` | Marketing contact form sender, team recipient, and reply-to |
| `FILE_STORAGE_DRIVER`, `LOCAL_STORAGE_PATH`, `S3_*`, `MINIO_*` | Private file storage configuration for approved sources and campaign assets |
| `MALWARE_SCANNER_HOST`, `MALWARE_SCANNER_PORT`, `MALWARE_SCAN_TIMEOUT_SECONDS` | Optional ClamAV-compatible INSTREAM scanner. Unset means uploads are marked unscanned; a configured but unavailable scanner rejects the upload. |
| `ALLOW_WORKSPACE_LLM`, `LLM_*`, `EMBEDDING_*` | External model provider settings; no live LLM or semantic embedding adapter is enabled, while source text extraction and local lexical vectors run without external providers |
| `SCAN_MAX_ASSETS`, `SCAN_MAX_CLAIMS`, `SCAN_TIMEOUT_SECONDS` | Per-scan asset, judgement-candidate and elapsed-time limits; one active scan per organisation |
| `OCR_PROVIDER`, `TESSERACT_COMMAND`, `TESSERACT_TIMEOUT_SECONDS` | Optional image OCR interface. Docker includes Tesseract; OCR stays off unless `OCR_PROVIDER=tesseract`. |
| `VERIFICATION_TOKEN_TTL_MINUTES`, `PASSWORD_RESET_TTL_MINUTES` | One-time account token expiry |

The workspace AI setting defaults off, and live provider adapters are absent. Do not add secrets to any `NEXT_PUBLIC_` variable.

## Implemented scope and assumptions

- The supplied product task includes architecture and data-model direction, approved-source and rules workflows, campaign scans, campaign comparison, findings and reviewer decisions.
- Users can register, verify email, sign in/out, reset passwords, and view/revoke their sessions. Organisations start in `pending_verification`; a platform administrator must approve them before workspace management and invites are available.
- Approved-source upload and review, version history, page/location passages, search, highlighting, and structured rules are available in Phase 2. Passages receive deterministic local hashed lexical vectors; they are not semantic model embeddings. Admins approve each source version, and rules cite passages from approved sources.
- Phase 3 provides campaign setup and versioned text, PDF, DOCX, PNG, JPEG, and WebP assets. Upload type is sniffed from content, image metadata is stripped, PDF/DOCX text is extracted, optional Tesseract OCR and ClamAV scanning are configurable, and asset updates invalidate prior scans. Perceptual logo comparison is a difference-hash prototype against Admin-approved logo files.
- Phase 4 provides queued, cancellable and resumable campaign scans with asset/rule snapshots, progress and per-organisation limits. Deterministic exact checks cover offer validity/discounts, banned and required phrases, logo version, channel limits, and language-scoped rules. The judgement interface uses top-five deterministic lexical-hash retrieval, strict validated JSON, evidence citation checks, confidence caps, and human-verification fallback. Model/prompt, retrieved passage IDs and latency are recorded without secrets. Campaign facts are normalized where possible and compared across assets; conflicts and unsupported facts remain review prompts. These checks are prototypes; no live LLM or semantic embedding provider is included.
- Phase 5 provides filtered and grouped findings, evidence and suggested-text comparison, creator edits as new asset versions, reasoned dismissal, clarification requests, and rescans. Reviewer submissions are idempotent and bind to exact asset versions and the current scan/rule snapshot; reviewers cannot review their own submissions. Approval, rejection, request-changes history, in-app notifications and email notices are recorded. Campaign status is set by the API. The workflow does not publish to platforms or certify legal or regulatory compliance.
- Phase 6 adds an expandable Evidence Map with source passage/page/version, expiry warnings for referenced offers, and Admin-only feedback suggestions after repeated creator decisions. Accepting a guideline suggestion records an Admin decision and never edits a rule. Brand Twin is an extractive assistant limited to effective approved passages; it cites each excerpt and refuses unmatched questions. Hindi exact checks and lexical retrieval are a limited-accuracy prototype. Instagram/LinkedIn-style previews use rule-based truncation and hashtag/link counts; they do not reflect live platform rendering or post content.
- Phase 7 adds a server-data dashboard, campaign and finding views, review queue, sources/rules, team and invite management, notification/AI settings, platform verification and append-only audit history. `/demo` is now a read-only sandbox backed by explicitly seeded sample records; it does not use editable browser-only state. Dashboard and finding APIs are tenant-scoped and list endpoints provide bounded filters and pagination.
- Invitation codes are stored as hashes, are scoped to one organisation and role, and have expiry/use limits. Accepted invitations create memberships. Platform administrators are assigned with the trusted CLI, not by self-service registration.
- The compose stack is the default full local environment. Docker is required for that path. If Docker is unavailable, marketing-only `npm run dev` remains available; API tests run with SQLite and do not require Docker.
- `NEXT_PUBLIC_SITE_URL` should be set to the real HTTPS domain before deployment. Resend requires an API key and verified sender. Production API sessions require a strong random `APP_SECRET_KEY`, a TLS endpoint, and `SESSION_COOKIE_SECURE=true`.
- Contact submissions use a process-local rate limit. Use shared Redis-backed limiting before running multiple Next.js instances in production.
- The privacy/security marketing copy describes the proposal's intended product posture and is not a compliance certification.

## Checks

```powershell
npm run lint
npm run typecheck
npm run build
Push-Location api
.venv\Scripts\python.exe -m pytest -q
Pop-Location
api\.venv\Scripts\python.exe api\scripts\run_evals.py
```

The GitHub Actions workflow runs the frontend lint/typecheck/build, API tests and the evaluation script with the mock judgement client. API tests use an isolated in-memory SQLite database and a fake email sender. The evaluation script also uses temporary SQLite and reports exact-type precision/recall, citation validity and false-breach rate. To evaluate a real model, implement an approved provider adapter behind `LLMClient`, set the deployment `LLM_*` values, enable `ALLOW_WORKSPACE_LLM`, and explicitly enable processing for a test organisation. No live provider adapter is included. Run `npm run start` after a successful build to inspect the production server.

## Deployment

Deploy Next.js and FastAPI as separate Node and Python services. Provision PostgreSQL with pgvector and Redis; set the backend environment variables on FastAPI and the public origin/backend URL on Next.js. Run `alembic upgrade head` as a release step before serving traffic. Configure private S3-compatible storage only when upload workflows are enabled. Set the trusted platform administrator with the CLI through a controlled operator process. Configure Resend sender verification, strong secrets, HTTPS and secure cookies. Keep the API and database private, and use shared rate limiting for the public contact route across instances.

## Requirements map

| # | Requirement | Implementation |
| ---: | --- | --- |
| 1 | Custom 404 | `app/not-found.tsx` |
| 2 | Favicon, touch/app/maskable icons and manifest | `app/favicon.ico`, `app/icon.svg`, `public/apple-touch-icon.png`, `public/icon-192.png`, `public/icon-512.png`, `public/maskable-icon-512.png`, `app/manifest.ts` |
| 3 | Loading skeletons and empty states | `app/(marketing)/demo/loading.tsx`, `app/(marketing)/demo/demo-loader.tsx`, `app/(marketing)/demo/demo-experience.tsx`, `app/app/page.tsx` |
| 4 | Toast notifications | `app/ui.tsx`, `app/(marketing)/demo/demo-experience.tsx`, `app/contact/contact-form.tsx` |
| 5 | Reduced-motion support | `app/globals.css` (`prefers-reduced-motion`) |
| 6 | Per-page 1200×630 social images | `app/opengraph-image.tsx`, `app/(marketing)/[slug]/opengraph-image.tsx`, `app/(marketing)/features/opengraph-image.tsx`, `app/(marketing)/demo/opengraph-image.tsx`, `app/og-image.tsx` |
| 7 | Typed, consent-gated tracking events | `app/track.ts`, `app/privacy-consent.tsx`, `app/ui.tsx`, `app/(marketing)/page.tsx`, `app/(marketing)/demo/demo-experience.tsx`, `app/contact/contact-form.tsx` |
| 8 | Cookie banner and preferences | `app/privacy-consent.tsx`, `app/consent.ts`, `app/ui.tsx`, `app/globals.css` |
| 9 | CSP and security headers | `proxy.ts`, `next.config.ts` |
| 10 | Validated, rate-limited contact email workflow | `app/api/contact/route.ts`, `app/contact/contact-form.tsx`, `.env.example` |
| 11 | Unique titles/descriptions and title template | `app/layout.tsx`, `app/(marketing)/[slug]/page.tsx`, `app/(marketing)/features/page.tsx`, `app/(marketing)/demo/page.tsx` |
| 12 | Open Graph and Twitter metadata | `app/layout.tsx`, marketing metadata files, generated social image files in #6 |
| 13 | Sitemap | `app/sitemap.ts` |
| 14 | Robots rules | `app/robots.ts` |
| 15 | Canonical tags and environment-based metadata base | `app/layout.tsx`, `site.config.ts`, `.env.example` |
| 16 | Organization, WebSite, SoftwareApplication, FAQPage and ContactPage JSON-LD | `app/structured-data.tsx`, marketing route components, `site.config.ts` |
| 17 | Breadcrumb navigation and BreadcrumbList JSON-LD | `app/ui.tsx`, `app/structured-data.tsx`, marketing route components |
| 18 | Related reading and contextual links | `app/ui.tsx`, `site.config.ts`, marketing route components |
| 19 | AVIF/WebP image optimisation with `next/image` | `next.config.ts`, `app/ui.tsx` |
| 20 | Lazy-loaded demo and graph | `app/(marketing)/demo/demo-loader.tsx`, `app/lazy-graph.tsx`, `app/graph.tsx` |
| 21 | Display and sans fonts through `next/font` | `app/layout.tsx` |
| P1 | Authentication, verification, reset, and sessions | `api/app/auth/router.py`, `api/app/auth/dependencies.py`, `app/auth/auth-form.tsx`, account routes under `app/` |
| P1 | Organisations, memberships, roles, invites, and verification | `api/app/orgs/router.py`, `api/app/orgs/settings_router.py`, `api/app/db/models.py`, `app/app/organisations/`, `app/app/invite/`, `app/app/admin/verifications/` |
| P1 | Tenant-aware product schema and migration | `api/app/db/models.py`, `api/alembic/versions/0001_initial.py` |
| P1 | Storage/AI boundaries, API proxy, and local service stack | `api/app/storage/`, `api/app/ai/`, `app/api/product/[...path]/route.ts`, `docker-compose.yml` |
| P1 | Generated OpenAPI TypeScript contracts | `api/openapi.json`, `api/scripts/export_openapi.py`, `app/lib/api-schema.d.ts`, `app/lib/api-client.ts` |
| P2 | Approved-source upload, parsing, chunking, versioning and approvals | `api/app/sources/documents.py`, `api/app/sources/router.py`, `api/app/db/models.py`, `api/alembic/versions/0002_approved_sources_and_rules.py` |
| P2 | Searchable source library, passage viewer and highlights | `app/app/organisations/sources/`, `app/app/organisations/[organizationId]/sources/page.tsx`, source API routes in `api/app/sources/router.py` |
| P2 | Evidence-linked structured rules and Admin suggestions review | `api/app/sources/schemas.py`, `api/app/sources/router.py`, `app/app/organisations/rules/`, `app/app/organisations/[organizationId]/rules/page.tsx` |
| P3 | Campaign setup, channel and date window, versioned assets, extraction and stale-scan invalidation | `api/app/campaigns/`, `api/app/assets/media.py`, `api/app/db/models.py`, `api/alembic/versions/0003_campaigns_and_asset_versions.py`, `app/app/organisations/campaigns/`, campaign route pages under `app/app/organisations/[organizationId]/campaigns/` |
| P3 | Optional ClamAV scanning, Tesseract OCR, metadata stripping and approved logo matching | `.env.example`, `docker-compose.yml`, `api/app/assets/media.py`, `api/app/campaigns/router.py`, `api/Dockerfile` |
| P4 | Asynchronous scans, exact checks, evidence validation, campaign fact comparison, progress and cancellation | `api/app/campaigns/scans.py`, `api/app/checks/judgement.py`, `api/app/worker.py`, `api/app/campaigns/router.py`, `app/app/organisations/campaigns/campaign-workspace.tsx` |
| P4 | Labelled evaluation set and metrics | `evals/brandlens.json`, `api/scripts/run_evals.py`, `api/tests/test_campaign_scans.py` |
| P5 | Filtered findings, creator resolution and clarification, version-bound review queue/history, notifications | `api/app/campaigns/router.py`, `api/app/notifications/`, `api/app/db/models.py`, `app/app/organisations/campaigns/campaign-workspace.tsx`, `app/app/organisations/reviews/` |
| P6 | Evidence Map, offer expiry warnings, feedback suggestions, bounded source Q&A and rule-based previews | `api/app/campaigns/router.py`, `api/app/campaigns/scans.py`, `api/app/checks/`, `app/app/organisations/brand-twin.tsx`, `app/app/organisations/campaigns/platform-preview.tsx` |
| P7 | Dashboard, findings and audit views, organization workspace navigation, read-only seeded sample workspace | `api/app/campaigns/router.py`, `api/app/orgs/router.py`, `api/app/sample/`, `api/scripts/seed_sample_workspace.py`, `app/app/organisations/dashboard.tsx`, `app/app/organisations/audit-log.tsx`, `app/app/organisations/[organizationId]/findings/`, `app/(marketing)/demo/` |

## Performance notes

The first viewport uses text and a small inline SVG graph rather than a large raster hero image. The demo is dynamically loaded, and public images use `next/image`. Fixed-size images and layout containers avoid image-driven layout shift. The consent controls are fixed-position. Re-run Lighthouse on the deployed origin after configuring the final domain and production runtime; cold server starts and deployment infrastructure affect LCP and total JavaScript measurements.
