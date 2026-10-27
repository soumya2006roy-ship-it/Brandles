# API endpoint matrix

Generated from `api/openapi.json` and cross-checked against FastAPI route handlers under `api/app/` on 2026-10-27. This is an implementation inventory, not proof that every route has end-to-end coverage.

Session authentication is cookie-based and resolved by custom request dependencies. `api/openapi.json` declares the `BrandLensSession` cookie scheme on protected operations and leaves health, login, registration, and password-reset operations public. Email verification endpoints have been removed for the hackathon build. The access column reflects handler dependencies and checks; test evidence is family-level rather than direct coverage of every row.

| Method | Route | Access requirement | Tenant scoped | Rate limited | Test evidence |
|---|---|---|---|---|---|
| GET | /health | Public / no session dependency | No | No | Partial — test_health.py; suite passed, not every route exercised directly |
| GET | /ready | Public / no session dependency | No | No | Partial — test_health.py; suite passed, not every route exercised directly |
| GET | /metrics | Public / no session dependency | No | No | Partial — test_health.py; suite passed, not every route exercised directly |
| POST | /api/v1/auth/register | Public / no session dependency | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/auth/login | Public / no session dependency | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/auth/logout | Signed-in session; tenant membership checked in handler where applicable | No | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/auth/me | Signed-in session; tenant membership checked in handler where applicable | No | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/auth/password-reset | Public / no session dependency | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/auth/password-reset/confirm | Public / no session dependency | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/auth/sessions | Signed-in session; tenant membership checked in handler where applicable | No | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| DELETE | /api/v1/auth/sessions/{session_id} | Signed-in session; tenant membership checked in handler where applicable | No | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs | Signed-in session; tenant membership checked in handler where applicable | No | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs | Signed-in session; tenant membership checked in handler where applicable | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id}/audit-events | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{organization_id}/invites | Organisation session: admin | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id}/invites | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| DELETE | /api/v1/orgs/{organization_id}/invites/{invite_id} | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{organization_id}/invites/{invite_id}/regenerate | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/invites/redeem | Signed-in session; tenant membership checked in handler where applicable | No | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/platform/verifications | Platform administrator session | No | No | Partial — test_security_controls.py; suite passed, not every route exercised directly |
| GET | /api/v1/platform/verifications/{organization_id}/history | Platform administrator session | Yes | No | Partial — test_security_controls.py; suite passed, not every route exercised directly |
| POST | /api/v1/platform/verifications/{organization_id}/decision | Platform administrator session | Yes | No | Partial — test_security_controls.py; suite passed, not every route exercised directly |
| PATCH | /api/v1/orgs/{organization_id}/settings | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id}/notification-preferences | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| PATCH | /api/v1/orgs/{organization_id}/notification-preferences | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id}/retention-settings | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| PATCH | /api/v1/orgs/{organization_id}/retention-settings | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{organization_id}/data-export | Organisation session: admin | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{organization_id}/data-deletion | Organisation session: admin | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/private-files/{organization_id}/{object_key} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_security_controls.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/sources | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/sources | Organisation session: admin | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/sources/{source_id} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/passages/{passage_id} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/sources/{source_id}/download | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/sources/{source_id}/approve | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/rules | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/rules | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/rules/{rule_id}/decision | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/dashboard | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/findings | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets | Organisation session: admin, creator | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/assets/{asset_id}/download | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans | Organisation session: admin, creator | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/cancel | Organisation session: admin, creator | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/resume | Organisation session: admin, creator | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id} | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/findings | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/scans/{scan_id}/facts | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/findings/{finding_id}/decision | Organisation session: admin, creator | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/findings/{finding_id}/clarification | Organisation session: admin, creator | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/submit | Organisation session: admin, creator | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/reviews/queue | Organisation session: reviewer | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/campaigns/{campaign_id}/reviews | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/reviews/{submission_id}/decision | Organisation session: reviewer | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/notifications | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| GET | /api/v1/orgs/{org_id}/guideline-update-suggestions | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/guideline-update-suggestions/{suggestion_id}/decision | Organisation session: admin | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/brand-twin/ask | Signed-in session; tenant membership checked in handler where applicable | Yes | Yes | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |
| POST | /api/v1/orgs/{org_id}/notifications/{notification_id}/read | Signed-in session; tenant membership checked in handler where applicable | Yes | No | Partial — test_auth_orgs.py; suite passed, not every route exercised directly |

Routes inventoried: **67**. Rate-limit status marks route-local `enforce_rate_limit`/login-delay calls; shared infrastructure or edge limits may apply separately. Auth and organization tests cover workflow families, but individual IDOR tests are not present for every route.
