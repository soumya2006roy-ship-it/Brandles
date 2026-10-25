# BrandLens

BrandLens is a marketing and product-showcase site for the source-based brand governance concept in `docs/brandlens-proposal.md`. It presents an editorial review workflow, the Campaign Consistency Graph, seven proposed innovations and a local skincare campaign simulation.

## Setup

Requirements: Node.js 20.9 or newer and npm.

```bash
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Source of truth and assumptions

- The workspace initially contained `BrandLens_Proposal update.docx`, but not the requested `docs/brandlens-proposal.md`. The supplied document’s paragraphs and five tables were converted to Markdown in `docs/brandlens-proposal.md`; the original DOCX is retained unchanged. The site copy uses that proposal.
- BrandLens is presented as a proposed concept, not a launched service. No customers, testimonials, performance statistics, third-party logos or pricing are claimed.
- The demo uses the imaginary skincare brand described in the proposal. Findings, evidence excerpts, confidence values, reviewer name and decisions are seeded simulation data in the browser. No demo content is sent to an AI service or platform.
- The Hindi consistency checker and Instagram/LinkedIn previews are simple rule-based prototypes. They do not promise perfect translation or exact real-platform rendering.
- The privacy and security pages describe the proposal’s intended approach, not a production certification.
- `NEXT_PUBLIC_SITE_URL` supplies the canonical public origin. The app falls back to `https://brandlens.example` if it is unset; configure the real domain before launch.
- `track()` dispatches typed browser events only after analytics consent. No analytics or marketing vendor script is installed.
- Contact rate limiting is an in-memory limit of five submissions per IP per hour per running process. Serverless or multi-instance deployments should replace it with a shared rate limiter. The IP key uses the hosting proxy’s `x-forwarded-for` or `x-real-ip` header.

## Environment variables

Copy `.env.example` to `.env.local`. Keep the Resend key server-side; never add a `NEXT_PUBLIC_` prefix to secrets.

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Yes for deployment | Canonical origin, metadata base, sitemap and social URLs |
| `RESEND_API_KEY` | Yes for contact email | Server-side Resend API key |
| `CONTACT_FROM_EMAIL` | Yes for contact email | Verified Resend sender address |
| `CONTACT_TO_EMAIL` | Yes for contact email | Team inbox for new submissions |
| `CONTACT_REPLY_TO` | Optional | Reply-to address on the sender confirmation |

The contact route returns a configuration error until the required Resend values are set.

## Verification

```bash
npm run lint
npm run typecheck
npm run build
npm run start
```

## Deploy

Deploy as a Node.js Next.js App Router application. Add the environment variables in the hosting provider, use the canonical HTTPS domain for `NEXT_PUBLIC_SITE_URL`, and verify the `CONTACT_FROM_EMAIL` sending domain in Resend. For production, put a shared rate limit store in front of `/api/contact` when the app runs on multiple processes.

The nonce-based Content Security Policy uses a per-request nonce through `proxy.ts`, so page HTML is rendered on request rather than served from a static export. Script execution and style elements require a nonce; `style-src-attr` has a narrow inline-style exception for Next Image’s generated fallback attribute. Keep the app behind a TLS endpoint; production responses add HSTS.

## Requirement map

| # | Requirement | Implementation |
| ---: | --- | --- |
| 1 | Custom 404 | `app/not-found.tsx` |
| 2 | Favicon, touch/app/maskable icons and manifest | `app/favicon.ico`, `app/icon.svg`, `public/apple-touch-icon.png`, `public/icon-192.png`, `public/icon-512.png`, `public/maskable-icon-512.png`, `app/manifest.ts` |
| 3 | Loading skeletons and empty states | `app/demo/loading.tsx`, `app/demo/demo-loader.tsx`, `app/demo/demo-experience.tsx` |
| 4 | Toast notifications | `app/ui.tsx`, `app/demo/demo-experience.tsx`, `app/contact/contact-form.tsx` |
| 5 | Reduced-motion support | `app/globals.css` (`prefers-reduced-motion`) |
| 6 | Per-page 1200×630 social images | `app/opengraph-image.tsx`, `app/[slug]/opengraph-image.tsx`, `app/features/opengraph-image.tsx`, `app/demo/opengraph-image.tsx`, `app/og-image.tsx` |
| 7 | Typed, consent-gated tracking events | `app/track.ts`, `app/privacy-consent.tsx`, `app/ui.tsx`, `app/page.tsx`, `app/demo/demo-experience.tsx`, `app/contact/contact-form.tsx` |
| 8 | Cookie banner and preferences | `app/privacy-consent.tsx`, `app/consent.ts`, `app/ui.tsx`, `app/globals.css` |
| 9 | CSP and security headers | `proxy.ts`, `next.config.ts` |
| 10 | Validated, rate-limited contact email workflow | `app/api/contact/route.ts`, `app/contact/contact-form.tsx`, `.env.example` |
| 11 | Unique titles/descriptions and title template | `app/layout.tsx`, `app/[slug]/page.tsx`, `app/features/page.tsx`, `app/demo/page.tsx` |
| 12 | Open Graph and Twitter metadata | `app/layout.tsx`, `app/[slug]/page.tsx`, `app/features/page.tsx`, `app/demo/page.tsx`, generated social image files in #6 |
| 13 | Sitemap | `app/sitemap.ts` |
| 14 | Robots rules | `app/robots.ts` |
| 15 | Canonical tags and environment-based metadata base | `app/layout.tsx`, per-page metadata files, `site.config.ts`, `.env.example` |
| 16 | Organization, WebSite, SoftwareApplication, FAQPage and ContactPage JSON-LD | `app/structured-data.tsx`, `app/[slug]/page.tsx`, `site.config.ts` |
| 17 | Breadcrumb navigation and BreadcrumbList JSON-LD | `app/ui.tsx`, `app/structured-data.tsx`, `app/[slug]/page.tsx`, `app/features/page.tsx`, `app/demo/page.tsx` |
| 18 | Related reading and contextual links | `app/ui.tsx`, `site.config.ts`, page components |
| 19 | AVIF/WebP image optimisation with `next/image` | `next.config.ts`, `app/ui.tsx` |
| 20 | Lazy-loaded demo and graph | `app/demo/demo-loader.tsx`, `app/lazy-graph.tsx`, `app/graph.tsx` |
| 21 | Display and sans fonts through `next/font` | `app/layout.tsx` |

## Performance notes

- Lighthouse desktop checks against the production server covered `/`, `/demo` and `/contact`. Each scored 100 for Performance, Accessibility, Best Practices and SEO. LCP was 0.6–0.8 s, CLS was 0–0.005 and TBT was 0 ms in these local runs. These measurements describe the local production build, not a deployed host.
- The first viewport has no large raster hero image: the main visual is a small, lazy-loaded inline SVG graph, and the largest content is text. The only `next/image` in the header is a 32×32 local icon with explicit dimensions.
- The hero graph uses CSS/SVG animation with a reduced-motion override. Fixed-size icon and content containers avoid image-driven layout shifts. The consent panel is fixed to the viewport and does not reserve or change document layout space.
- Lighthouse reports 23–27 KiB of potential unused JavaScript in a shared client chunk. Demo interactions load through a separate client chunk, and the graph has its own dynamic chunk. No analytics/marketing vendor bundle is installed.
- The nonce-based CSP requires request rendering. This may raise time-to-first-byte on cold serverless starts; use a warm Node runtime or edge caching compatible with per-request nonces, and measure with Lighthouse after deployment.
