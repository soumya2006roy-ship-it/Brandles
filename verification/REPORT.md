# BrandLens feature verification report

Generated: 2026-10-31 23:02 IST  
Environment: local Docker Compose on Windows; Next.js development server; FastAPI; PostgreSQL 17 with pgvector; Redis; background worker; Mailpit. `LLM_PROVIDER=none` and `OCR_PROVIDER=none`. No production deployment was involved.

## Summary

Brand Health analytics and the Visual Compliance prototype were exercised in a browser against a fresh, isolated `[DEMO DATA]` workspace. The analytics UI and its filtered API responses agreed for date, campaign, severity, and content-type filters. The visual checks identified the generated off-palette poster, rendered a selectable image-level finding, and persisted resolve, dismiss, and false-positive actions. Invalid, corrupt, and oversized uploads displayed errors. The existing campaign text scan also completed.

The run did **not** demonstrate wrong-logo detection or OCR-based missing-disclaimer detection: the synthetic visual workspace had no approved image logo source, and OCR was disabled. These are recorded as `OBSERVED`, not passed. The logo matching path has separate API regression coverage in the existing API suite. Typography and image-level location remain heuristic or unverifiable as described below.

## Repository and runtime notes

- Stack: Next.js 16.4.3 App Router, React 19, TypeScript, Tailwind CSS 4; FastAPI on Python 3.12, SQLAlchemy and Alembic; PostgreSQL 17 + pgvector; Redis-backed work queue and rate limits; Mailpit for local email.
- Run the full local environment from the repository root with `start.bat` on Windows or `bash start.sh` on macOS/Linux. Direct Docker Compose use is `docker compose up --build`. Compose runs `alembic upgrade head` before starting the API. README has the prerequisites and generated local-admin setup.
- Campaign scan results are persisted as `Scan`, `Finding`, and `ExtractedFact` rows, with review and resolution activity in `Review` and append-only `AuditEvent` records. Brand Health aggregates these records at request time; it does not use materialized metric snapshots.
- Approved logo comparisons use the existing image-level difference-hash prototype, with a match threshold of 0.90. It compares whole images and does not locate or extract a logo from a poster.
- Current schema was verified at Alembic head `0010_expand_finding_status`.
- Initial pre-change baseline output was not captured by this continuation because the analytics implementation was already committed before this verification pass. The final test results below are direct runs against the current tree.

## Startup and commands

Startup output is preserved in [`startup.log`](startup.log) and [`startup-services.log`](startup-services.log). The stack was running; API `/ready` returned HTTP 200 and the web login page returned HTTP 200. The local API migration check reported `0010_expand_finding_status (head)`.

Commands run from the repository root:

```powershell
npm run lint
npm run typecheck
npm test
$env:PLAYWRIGHT_SKIP_WEBSERVER='1'; npm run test:e2e
npm run build
npm run simulate:health
api\.venv\Scripts\python.exe -m pytest -q
node verification/run-simulation.mjs
```

Results:

- `npm run lint` — passed with no warnings on the final rerun.
- `npm run typecheck` — passed.
- `npm test` — 3 test files, 8 tests passed.
- `npm run test:e2e` — 6 Playwright tests passed, including public-page accessibility checks.
- `npm run build` — passed; production routes compiled and standalone output prepared. Contrast checks passed for the project’s listed theme tokens.
- `npm run simulate:health` — completed 15 synthetic campaign scenarios across three simulated organisations; non-persistent.
- `api\.venv\Scripts\python.exe -m pytest -q` — 61 passed, 1 skipped. One upstream Starlette/httpx deprecation warning was emitted.
- `node verification/run-simulation.mjs` — completed; scenario-by-scenario outcomes are recorded in [`simulation-results.json`](simulation-results.json). Forced 503 and rejected 415/413 upload responses are expected test inputs, not unexpected regressions.

## Browser scenarios

Screenshots are in [`screenshots/`](screenshots/). The numbered images correspond to these scenarios:

| Result | Scenario | Evidence |
| --- | --- | --- |
| PASS | Dashboard at desktop width; API cross-check: 90% compliance, 81 open findings, 120 scans | `01-brand-health-desktop.png` |
| PASS | Date filter; 120 scans reduced to 28 and UI matched the API | `02-brand-health-date-filter.png` |
| PASS | Campaign filter; one selected campaign and 7 scans matched the API | `03-brand-health-campaign-filter.png` |
| PASS | High-severity filter; rendered summary and campaign rows matched API | `04-brand-health-severity-filter.png` |
| PASS | Text content-type filter; rendered summary and campaign rows matched API | `05-brand-health-content-filter.png` |
| PASS | Current filtered-view CSV downloaded and contained summary columns | `06-brand-health-export.csv` |
| PASS | Future date range displayed the empty state | `07-brand-health-empty-state.png` |
| PASS | Test-only 503 displayed the retry/error state | `08-brand-health-error-state.png` |
| PASS | Responsive screenshots at 768px and 390px | `09-brand-health-tablet-768.png`, `10-brand-health-mobile-390.png` |
| PASS | Generated compliant-palette poster had no palette deviation | `11-visual-compliant-poster.png` |
| OBSERVED | Wrong-logo fixture did not produce a mismatch without a configured approved image logo rule | `12-visual-wrong-logo.png` |
| PASS | Off-brand palette generated a deviation; selected finding and image overlay synchronized | `13-visual-off-brand-colours.png`, `16-visual-finding-open.png` |
| OBSERVED | Missing-disclaimer fixture produced no finding because OCR was disabled | `14-visual-missing-disclaimer.png` |
| OBSERVED | Blurry fixture only generated a 65% confidence informational palette signal requiring human review; no blur detector is implemented | `15-visual-blurry-low-quality.png` |
| PASS | Resolve, dismiss with reason, and false-positive actions persisted | `17-visual-finding-resolved.png`, `18-visual-finding-dismissed.png`, `19-visual-finding-false-positive.png` |
| PASS | Renamed text file and corrupt image were rejected with clear messages | `20-visual-invalid-extension.png`, `21-visual-corrupt-image.png` |
| PASS | UI rejected a generated >25 MiB PNG; a direct full-body browser upload passed through Next.js and API returned 413 | `22-visual-oversized-image.png` |
| PASS | Existing campaign workspace opened and Instagram text scan completed with 11 findings | `23-regression-campaign-workspace.png`, `24-regression-text-scan-completed.png` |
| OBSERVED | Browser regression workspace had no approved image logo source, so comparison output was not available. Existing API positive/negative logo-match tests passed within the API suite. | `23-regression-campaign-workspace.png` |
| PASS | 20 keyboard Tab transitions on each new page; Enter toggled theme on Visual Compliance; Escape left no dialog open | `25-visual-keyboard-access.png` |
| PASS | Axe found 0 violations on Brand Health and Visual Compliance | recorded in `simulation-results.json` |

The UI originally sent image uploads through a Next.js proxy whose default client-body buffer was 10 MB. This truncated an otherwise valid 25 MB asset before the API could validate it. `next.config.ts` now sets `proxyClientMaxBodySize` to 30 MB, leaving headroom for multipart encoding. The final simulation confirmed the UI guard and API 413 response both work.

### Browser console and network

No unexpected JavaScript errors, failed requests, or non-test HTTP errors were recorded in the simulation. The test deliberately generated one analytics 503 to inspect the error state, two 415 upload rejections, and one 413 oversized upload rejection. A browser navigation request was aborted during the login redirect. These expected events are listed in `simulation-results.json`.

## Bugs found and fixed

1. **Large image body truncated by Next.js proxy** — raised the proxy buffer to 30 MB and verified API-level 25 MB validation with a generated oversized image.
2. **Decorative analytics bar triggered an accessible-name audit** — marked the non-interactive bar as decorative; its numerical value remains visible as text.
3. **Workspace brand link had a redundant accessible label** — removed the override so the visible link text supplies its name.
4. **Simulation filter check counted unrelated tables** — scoped its row assertion to the campaign comparison table and made KPI comparisons against each filtered API response.

## Accuracy limitations

- Dominant-colour extraction with CIEDE2000 is deterministic but poster-level and heuristic; the bounding box covers the image, not the exact colour patch. Validate tolerance against real approved artwork.
- Logo matching is the existing perceptual difference-hash prototype over whole images. It is not logo-region detection and should not be used as proof of logo placement or exact mark identity.
- Disclaimer detection requires optional OCR/Tesseract. With `OCR_PROVIDER=none`, the scan reports the check as unavailable/not verifiable and does not assert missing copy.
- Typography/font family recognition is not implemented and is reported as not verifiable.
- Bounding boxes are approximate; low-confidence findings are marked for human review.
- The generated fixtures are synthetic. The wrong-logo and missing-disclaimer visual outcomes did not pass in this run. Do not infer performance on real assets from these fixture results.
- No real LLM provider, email provider, malware scanner, public deployment, or production storage service was configured or verified.

## Setup and provider notes

- Brand Health demo seed: `api\.venv\Scripts\python.exe api\scripts\seed_brand_health.py --email <existing-account-email> --confirm-demo-data`. It refuses production mode and creates a clearly marked isolated workspace. Use the `generate_visual_fixtures.py` script for synthetic assets.
- Current verification needs no LLM key or OCR executable. For optional OCR, configure the documented OCR environment/provider and install Tesseract where the API runs; then rerun the synthetic disclaimer tests. Font recognition remains unavailable.
- Private local file storage was used. Production should configure the S3-compatible storage settings listed in `.env.example`; never commit credentials.
- Exact schema migration path is `api/alembic/versions/0010_expand_finding_status.py`; apply with `alembic upgrade head` from `api/` after configuring `DATABASE_URL`.

## Changelog

### Added

- `api/alembic/versions/0010_expand_finding_status.py`
- `api/app/assets/visual.py`
- `api/scripts/generate_visual_fixtures.py`
- `api/tests/test_visual_compliance.py` and generated synthetic fixtures under `api/tests/fixtures/visual/`
- `app/app/organisations/visual-compliance/` and `app/app/organisations/[organizationId]/visual-compliance/`
- `verification/run-simulation.mjs`, `verification/generate-oversized-fixture.py`, startup logs, results JSON, screenshots, and this report.

### Modified

- `api/app/campaigns/router.py`, `scans.py`, `schemas.py`, `api/app/core/config.py`, `api/app/db/models.py`, `api/app/sources/schemas.py`
- `api/scripts/seed_brand_health.py`
- `app/app/organisations/brand-health/brand-health-dashboard.tsx`, `app/app/organisations/rules/rules-editor.tsx`, `app/app/product-shell.tsx`, `app/globals.css`, `app/lib/api-client.ts`, `app/lib/api-schema.d.ts`
- `next.config.ts`, `.env.example`, `.gitignore`, `README.md`, `api/openapi.json`, `docs/api.md`, and `docs/decisions.md`

