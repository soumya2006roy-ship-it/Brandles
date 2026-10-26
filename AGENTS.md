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

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
