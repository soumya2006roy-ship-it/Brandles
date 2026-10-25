# Product implementation decisions

The user-provided product brief contains product rules, architecture, data model, and detailed Phase 1-3 requirements. Campaign scan generation, finding management, and reviewer-approval behavior remain unspecified.

- The existing BrandLens public site and its content remain grounded in `docs/brandlens-proposal.md`. Product assumptions do not create new customer claims or pricing.
- The site and API run as separate Next.js and FastAPI services. PostgreSQL with pgvector stores tenant-scoped records; Redis provides shared queue/rate-limit infrastructure; local compose provisions private MinIO and Mailpit.
- A user must verify email to authenticate. New organisations are pending review. A platform operator grants administrator status via a trusted CLI after database access, and cannot approve their own submitted organisation.
- Invitations are random, expiring, role-scoped and use-limited. Only a one-way hash is persisted. Sessions use HTTP-only cookies and password hashes use Argon2id.
- Source documents are parsed with PyMuPDF and python-docx, chunked with overlap, and stored with page/location references. The current local vector is a deterministic lexical hash representation for prototype retrieval, not a semantic embedding model.
- Only Admin-approved source versions with effective dates are current evidence. New versions archive earlier approved versions for that source family, and rules tied to superseded versions are archived. Creator-created rules remain suggestions until Admin approval.
- AI remains mock-only. Source and asset content is not sent to an LLM. Workspace and deployment permissions remain separate gates for any future external model use.
- Campaign scans, findings, and reviewer approval remain scaffolding until their workflow behavior is specified.
- Campaigns scope channels, dates and language. Each asset group retains immutable versions; replacing an asset marks asset-level and campaign-level scans stale and their findings stale.
- Upload types are detected from signatures/content rather than filename extensions. Files have size limits, optional ClamAV scanning fails closed when configured, and accepted raster images are re-encoded without metadata.
- PDF and DOCX text extraction is enabled for assets. OCR is behind a provider interface and may use Tesseract when configured. Prototype approved-logo matching uses perceptual difference hashes against approved image source versions and is not a vision model.
- Storage drivers use private local/S3-compatible paths and organization-scoped access; source and campaign asset upload/download are enabled.
- Docker is the simplest complete local launch path. `npm run dev` intentionally remains useful for the public marketing site alone.
- The backend has test coverage using SQLite and fake email. Production use still requires infrastructure configuration, a security review, and the later workflow implementation.
