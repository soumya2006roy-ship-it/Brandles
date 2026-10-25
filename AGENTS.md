# AGENTS.md

## Project
BrandLens marketing and product-showcase website. The source of truth for all content is `docs/brandlens-proposal.md`. Never invent customers, testimonials, statistics, logos or pricing. Be honest that the Hindi checker and platform previews are simple rule-based prototypes.

## Stack
Next.js (App Router, TypeScript), Tailwind CSS, `next/font`, `next/image`, Metadata API, Zod, Resend for email. No heavy UI libraries.

## Commands (run after every phase and fix all failures)
- `npm run lint`
- `npm run typecheck`
- `npm run build`

## Rules
- Accessible (WCAG AA), responsive, dark mode, respects `prefers-reduced-motion`.
- No non-essential scripts load before cookie consent.
- Secrets only via env vars; keep `.env.example` current.
- Central config in `site.config.ts`.
- Work in small commits, one per phase.
