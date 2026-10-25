# Product implementation decisions

The user-provided product brief contains product rules, architecture, data model, detailed Phase 1 requirements, and now detailed Phase 2 approved-source/rule and Phase 3 campaign/asset requirements. Campaign scans, findings, and reviewer-approval behavior remain unspecified.

- The existing BrandLens public site and its content remain grounded in `docs/brandlens-proposal.md`. Product assumptions do not create new customer claims or pricing.
- The site and API run as separate Next.js and FastAPI services. PostgreSQL with pgvector stores tenant-scoped records; Redis provides shared queue/rate-limit infrastructure; local compose provisions private MinIO and Mailpit.
- A user must verify email to authenticate. New organisations are pending review. A platform operator grants administrator status via a trusted CLI after database access, and cannot approve their own submitted organisation.
- Invitations are random, expiring, role-scoped and use-limited. Only a one-way hash is persisted. Sessions use HTTP-only cookies and password hashes use Argon2id.
- Source documents are parsed with PyMuPDF and python-docx, chunked with overlap, and stored with page/location references. The current local vector is a deterministic lexical hash representation for prototype retrieval, not a semantic embedding model.
- Only Admin-approved source versions with effective dates are current evidence. New versions archive earlier approved versions for that source family, and rules tied to superseded versions are archived. Creator-created rules remain suggestions until Admin approval.
- AI remains mock-only. Source and asset content is not sent to an LLM. Workspace and deployment permissions remain separate gates for any future external model use.
- Campaign scans, findings, and reviewer approval remain scaffolding until their workflow behavior is specified.
- Storage drivers use private local/S3-compatible paths and organization-scoped access; source upload/download is enabled.
- Docker is the simplest complete local launch path. `npm run dev` intentionally remains useful for the public marketing site alone.
- The backend has test coverage using SQLite and fake email. Production use still requires infrastructure configuration, a security review, and the later workflow implementation.
