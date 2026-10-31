# Security and privacy operations

## Implemented controls

- Organisation IDs are included in resource queries; membership roles are checked at protected routes. Reviewers cannot approve their own submissions, and the API prevents platform administrators from deciding verification for an organisation they submitted.
- Inputs use strict Pydantic schemas. Session cookies are HttpOnly, SameSite=Lax and Secure in production. Mutations validate browser Origin and Fetch Metadata. Both apps set security headers; production requires a strong API secret and secure cookies.
- Signup does not require email verification. New accounts must set an account recovery question; its normalized answer is Argon2-hashed, never returned by APIs, and recovery attempts are rate limited. A successful answer resets the password and revokes active sessions. Recovery answers can be guessable, so this is a convenience fallback for the hackathon; email reset remains available.
- Development Compose ports bind to `127.0.0.1`; the API container requires `APP_SECRET_KEY` from the local environment instead of using a known fallback. Production still requires private network ingress and managed secrets.
- Production throttles use Redis with atomic increments, bounded windows and `Retry-After`. Client forwarding headers are trusted only when the direct peer is in `TRUSTED_PROXY_CIDRS`. `RATE_LIMIT_MULTIPLIER` scales source-defined quotas; default is 1.
- The Next.js contact route shares its five-per-hour limit through Redis, hashes client addresses in Redis keys, ignores `X-Forwarded-For`, and trusts only `X-Real-IP` supplied by an ingress configured to overwrite it. It returns `Retry-After` on 429 and fails closed with 503 if production Redis is unavailable. Development has a bounded process-local fallback.
- Upload routes validate detected formats and size limits, store private objects under random keys, check tenant access on download and return short-lived signed URLs. OCR and malware scanning are optional; configure their tools/services before relying on those checks.
- Asset and source text is treated as untrusted input in model prompts. Model results are schema-validated and cited excerpts are checked against approved passage text. Provider use is disabled by default.
- Audit events are append-only and omit invitation secrets and full document bodies. Organisation export/deletion and retention controls are available. Data in transit depends on the deployment's TLS ingress and managed-service configuration.

## Limits and deployment responsibilities

This repository is not a certification or legal assessment. Metrics are process-local and can reset on restart. Real semantic embeddings, production LLM provider wiring, malware/OCR services, managed backups, retention infrastructure, secret rotation and alerting require deployment setup. Use a secrets manager; do not commit `.env`. Restrict database, Redis and object storage networks. Configure lifecycle policies and encryption for managed object storage, encrypted database volumes/backups, and TLS for internal service connections where supported.

Review privacy terms with counsel, complete the AI vendor DPA before sending organisation content to a provider, and set appropriate retention and deletion policies for the operating jurisdiction.
