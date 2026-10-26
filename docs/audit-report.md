# BrandLens website and launch audit

Audit updated: 2026-10-26. Product claims are checked against `docs/brandlens-proposal.md`.

## Baseline and launcher findings

- `npm run lint`, `npm run typecheck`, `npm run build`, `npm test`, and browser checks passed before the latest changes.
- Production startup was corrected to use Next.js standalone output. Production smoke requests returned HTTP 200 for `/`, icons, robots and sitemap, and HTTP 404 for an unknown path.
- Windows launcher reproduction established why the organisation workspace was unavailable: if Docker is missing or stopped, the launcher ran the web app alone. The web app responded on port 3000, but API 8000 and database, Redis, storage and mail ports had no listeners. See `docs/launch-diagnosis.md`.
- The launcher will be changed to require the complete Compose stack and stop with a clear prerequisite error when Docker cannot start. It will no longer claim full product startup while only serving the public website.

## Prioritized work

### P0 Critical

- None identified in the latest static checks. This is not a penetration test or security certification.

### P1 High

- **Full-stack launch reliability:** launcher starts only the public web service on systems without Docker. Phase 3 will make it fail clearly and launch all services with readiness checks when Docker is available.
- **The unauthenticated public workspace endpoint:** remove its page, API, seed data, tracking events and migration field. Product screens must use account and organisation APIs only.
- **Runtime judgement fallback:** development used a fixed insufficient-evidence provider. Remove that runtime provider; keep deterministic fixtures confined to evaluation/test code so unavailable judgement remains an explicit human-verification state.
- **Acceptance coverage remains incomplete:** Docker was not installed, so database migrations, API runtime and full signup-to-approval journey cannot be run here. Report this limit plainly.

### P2 Medium

- **Product entry points:** replace public calls to action with organisation creation, login, invite redemption and contact links. Ensure sitemap, metadata, breadcrumbs and related reading contain only active routes.
- **Prototype disclosures:** Hindi phrase checks and platform previews remain limited rule-based prototypes; no wording should imply production translation, publishing or exact platform rendering.
- **Verification coverage:** Lighthouse, full route metadata crawl, consent network capture, keyboard coverage, responsive widths and product-route accessibility remain incomplete.

## Verification record

The previous website audit verified five unit tests, five browser tests, contrast token thresholds, a production standalone page/theme smoke check, and zero high-severity npm audit findings. For the current removal and launcher work, rerun lint, typecheck, build, API pytest, unit tests, browser tests, route/link checks and repository search after implementation. Docker-backed startup cannot be verified in this environment because Docker is not installed.

## Remaining risks

Redis-backed production rate limiting, real email delivery, database migration in a clean Postgres instance, Docker images, Lighthouse scores and the complete authenticated product workflow still require configured infrastructure. No claim of full production readiness is made until those checks have actual run results.
