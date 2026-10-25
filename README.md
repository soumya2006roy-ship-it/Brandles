# BrandLens

BrandLens is an editorial marketing and product-showcase site for an AI-assisted brand governance concept. It presents the source-based review workflow, the Campaign Consistency Graph and a seeded skincare campaign simulation.

## Setup

Requirements: Node.js 20.9 or newer and npm.

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Source of truth

The supplied `BrandLens_Proposal update.docx` was present in the project, while the requested `docs/brandlens-proposal.md` was absent. Its paragraphs and five tables were converted into `docs/brandlens-proposal.md` and used as the content source. The original document is retained unchanged.

## Assumptions

- BrandLens is presented as a proposed concept, not a launched service. No customer names, testimonials, performance statistics, logos or pricing are claimed.
- The demo scenario is the imaginary skincare brand described in the proposal. Its findings, evidence, confidence values and reviewer details are seeded simulation data kept in the browser.
- The Hindi checker and Instagram/LinkedIn previews are simple rule-based prototypes. They do not promise perfect translation or exact real-platform rendering.
- The privacy and security pages describe the proposal’s intended design, not a production compliance or security certification.
- `NEXT_PUBLIC_SITE_URL` is the canonical public origin. Until configured, local metadata uses `https://brandlens.example` as a placeholder.

## Environment variables

Copy `.env.example` to `.env.local` and set the values needed for the features you enable. Secrets belong only in server-side environment variables; never expose Resend credentials with a `NEXT_PUBLIC_` prefix.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Canonical site URL, metadata base and social URLs |
| `RESEND_API_KEY` | Resend key used by the contact endpoint |
| `CONTACT_FROM_EMAIL` | Verified sender address for contact email |
| `CONTACT_TO_EMAIL` | Team inbox receiving submissions |
| `CONTACT_REPLY_TO` | Optional reply-to address |

## Build and deploy

```bash
npm run lint
npm run typecheck
npm run build
npm run start
```

Deploy as a standard Next.js App Router application. Set the environment variables in the hosting provider, configure the public domain as `NEXT_PUBLIC_SITE_URL`, and verify the Resend sender domain before enabling contact email delivery.

## Requirements map

Implementation mapping for the 21 numbered requirements will be completed after all phases are implemented.
