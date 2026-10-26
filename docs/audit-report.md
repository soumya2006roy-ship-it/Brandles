# BrandLens website audit

Audit started: 2026-10-26. Scope: repository routes, public copy, metadata, consent/tracking, UI controls, contact handler, security headers, assets, and available automated checks. Product claims are compared with `docs/brandlens-proposal.md`.

## Baseline

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed; the built-in theme token contrast check passed.
- `npm test`: passed, 2 Vitest tests.
- `npm run test:e2e`: passed, 4 Chromium tests (public smoke, read-only sample label, theme toggle, axe on the four public pages).
- `npm run start`: fixed to launch the generated standalone server. Production smoke checks returned HTTP 200 for `/`, icons, `/robots.txt` and `/sitemap.xml`, and HTTP 404 for an unknown path. A production browser run passed public route smoke, read-only demo, theme toggle and axe checks.
- `npm test`: passed, 5 tests across 2 files, including contact rate-limit unit/concurrency coverage.
- `npm run test:e2e` with a local dev server: passed, 5 Chromium checks including contact validation and six-request rate limiting with `Retry-After`. The five requests returned the expected dev 503 because no Resend key is configured; request six returned 429.
- `npm audit --audit-level=high`: passed, 0 known vulnerabilities.
- No Docker/production database/browser network crawl, Lighthouse run, external email delivery, or real AI provider run was performed as part of this baseline.

## Route and control inventory

Public routes include `/`, `/{problem,how-it-works,campaign-consistency-graph,features,demo,roles,security,roadmap,contact,privacy,cookies}`, `/404`, auth routes `/login`, `/sign-up`, `/verify-email`, `/forgot-password`, `/reset-password`, product routes under `/app`, and `/api/contact` plus `/api/product/[...path]`. Generated routes include sitemap, robots, manifest, favicon/icons, and Open Graph images. The App Router also has loading states for `/demo` and the product shell; no general route `error.tsx` was found at audit start.

Interactive controls include desktop/mobile navigation, the light/dark theme button, public CTAs and tracked links, sample-workspace disclosures, consent banner/preferences, contact form, toast dismissal, auth forms, organisation onboarding, tabs/forms/search/filter/pagination in campaign/source/rules/finding/review screens, evidence drawers, finding resolution/dismissal, review decisions, Brand Twin, platform preview, account sessions and admin verification.

## Prioritized findings

### P0 Critical

- None confirmed in the baseline static checks. This is not a security certification or full production penetration test.

### P1 High

- **Production startup and local standalone assets.** Fixed `npm start` and standalone output preparation. Verified production home, static asset, icons, robots, sitemap, 404, theme hydration and axe on four public routes. The standalone server was not run inside Docker.
- **Contact throttling depended on spoofable, process-local identity.** Replaced direct `X-Forwarded-For` use with a shared atomic Redis counter in production, hashed IP keys, bounded local development fallback, `Retry-After`, and fail-closed behavior when Redis or a valid trusted `X-Real-IP` is missing. E2E verified the dev behavior and spoofed `X-Forwarded-For` does not rotate the identity. Redis-backed multi-replica behavior still needs deployment verification.
- **Acceptance coverage is incomplete.** Existing browser tests cover four public routes and do not exercise consent, contact delivery/validation/rate limiting, all public routes/metadata, keyboard flows, responsive widths, or the seeded organisation journey. Axe runs only on four public pages in the default theme. Add focused tests where credentials/runtime permit; explicitly list unavailable checks.

### P2 Medium

- **Demo is a read-only seeded workspace, not the earlier interactive browser simulation.** The current `/demo` page accurately labels itself read-only and depends on the sample seed command; it does not expose scan/resolve/approve actions or a date-sensitive expiry finding. Preserve the prior read-only sandbox requirement and explain this mismatch instead of presenting an interactive workflow as implemented.
- **The older, unused browser demo component contains invented confidence percentages and sample file version details.** The active `/demo` is the read-only seeded API workspace. The legacy simulation is not part of that route; remove unsupported numbers and overly specific invented file names from the legacy component or delete it if references confirm it is unused.
- **Design audit coverage is partial.** Automated axe coverage and contrast-token checks do not cover every route, theme, viewport, zoom level, keyboard path, runtime request, or image/font delivery.
- **Metadata/SEO checks have not been crawled route-by-route.** Code provides metadata, sitemap, robots, JSON-LD and canonical settings, but uniqueness, actual production response status, every social image, and links need runtime verification.

### P3 Polish

- No verified polish-only defect recorded yet. Visual/real-device review remains outstanding.

## Applied fixes and follow-up

Production startup and contact throttling have been fixed and rechecked. Remaining items are tracked with honest evidence in `docs/requirements-matrix.md`; full journey, provider-backed email, consent network capture, exhaustive accessibility, Lighthouse and Docker checks remain incomplete or require deployment credentials/runtime.
