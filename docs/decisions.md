# Product implementation decisions

The user-provided product brief at implementation time contains product rules, an architecture, a data model, and detailed Phase 1 requirements for authentication, organisations, roles, verification, and invitations. It does not include detailed behavior for the later source-ingestion, scan, findings, or reviewer-approval phases. This implementation delivers the specified Phase 1 product surface and establishes schemas and service boundaries for future work without pretending those workflows are live.

- The existing BrandLens public site and its content remain grounded in `docs/brandlens-proposal.md`. Product assumptions do not create new customer claims or pricing.
- The site and API run as separate Next.js and FastAPI services. PostgreSQL with pgvector stores tenant-scoped records; Redis provides shared queue/rate-limit infrastructure; local compose provisions private MinIO and Mailpit.
- A user must verify email to authenticate. New organisations are pending review. A platform operator grants administrator status via a trusted CLI after database access, and cannot approve their own submitted organisation.
- Invitations are random, expiring, role-scoped and use-limited. Only a one-way hash is persisted. Sessions use HTTP-only cookies and password hashes use Argon2id.
- AI and embedding providers are mock-only. No source or campaign processing is enabled. Workspace permission and deployment permission are both required before later AI work can be enabled.
- The schema includes likely Phase 2 product entities as persistence scaffolding. They are not exposed through upload or scan APIs and contain no seeded customer or campaign data.
- Storage drivers support private local/S3-compatible paths but no product upload interaction is available yet.
- Docker is the simplest complete local launch path. `npm run dev` intentionally remains useful for the public marketing site alone.
- The backend has test coverage using SQLite and fake email. Production use still requires infrastructure configuration, a security review, and the later workflow implementation.
