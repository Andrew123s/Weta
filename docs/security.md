# Security architecture

Industrial process data, formulations and waste flows are commercially sensitive, and reports may be used in regulatory proceedings. The security goals are confidentiality between organizations, integrity of results and audit records, and availability adequate for professional use.

## 1. Authentication

- Passwords: Argon2id (`argon2-cffi`) with parameters at or above current OWASP guidance, per-user salt, optional server-side pepper from the environment. Minimum length 12, checked against a breached-password list (offline k-anonymity file or API, configurable). No composition rules that reduce entropy.
- MFA: TOTP (RFC 6238) with recovery codes; can be enforced per organization.
- Sessions: access token (JWT, about 10 minutes) kept in memory; rotating opaque refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, stored hashed; reuse detection revokes the token family.
- Lockout and throttling: progressive delay and temporary lock per account and per IP.
- Password reset: single-use, short-lived, hashed tokens; responses do not reveal whether an account exists.
- API keys for machine access: shown once, stored hashed, scoped, expiring.
- OIDC single sign-on as a later, optional provider.

## 2. Authorization (RBAC with scope)

Permission codes are `<resource>.<action>`: for example `project.read`, `facility.write`, `scenario.run`, `scenario.lock`, `dataset.import`, `ml.train`, `ml.promote`, `rules.import`, `report.build`, `report.approve`, `audit.read`, `admin.users`.

| Role | Intent |
|------|--------|
| owner | Everything in the organization, including billing and deletion |
| admin | Users, roles, datasets, rule packs |
| analyst | Create and edit project data, run scenarios, build reports |
| reviewer | Read everything in assigned projects, approve reports, lock scenarios |
| viewer | Read-only in assigned projects |
| regulator_readonly | Read-only access to specific final reports and their traces, time-limited |

Checks happen at three levels:

1. Route dependency: `require("scenario.run")`.
2. Object scope: the object's organization and project must match the caller's memberships. Identifier guessing must return 404, not 403.
3. Database: row-level security on `organization_id` using `SET LOCAL app.org_id` per transaction, with the application connecting as a non-owner role that cannot bypass RLS. A bug in application filtering therefore does not expose another tenant's rows.

Background jobs carry the initiating user's identity and scope and re-check permissions when they start.

## 3. Input validation

- All request bodies validated by Pydantic models with strict types, bounded lengths and numeric ranges; unknown fields rejected.
- Units validated against the controlled unit list; CAS numbers checksum-validated.
- SQL only through SQLAlchemy with bound parameters. No string-built SQL, including in spatial queries.
- Geometry: validity, coordinate range, vertex-count and area limits before any spatial operation.
- Rule applicability expressions and report template configs are parsed by a restricted grammar; nothing from user data is evaluated as code. Jinja templates for reports are system-owned and autoescaped; users cannot upload templates.
- Outputs: React escapes by default; no `dangerouslySetInnerHTML` with user content; CSV and Excel exports neutralize formula-leading characters to prevent formula injection.

## 4. File validation

Upload pipeline, before any domain parser runs:

1. Size limit per type and per organization quota; streaming to a quarantine directory outside the web root.
2. Type detection by content signature, not by extension or client MIME; allow-list per endpoint (GeoPackage, GeoJSON, zipped shapefile, GeoTIFF, CSV, XLSX, PDF, EcoSpold, ILCD zip, JSON-LD zip).
3. Archive safety: reject path traversal, symlinks, nested-archive depth and decompression-ratio bombs.
4. Optional antivirus scan with natively installed ClamAV.
5. Parse in a worker process with time and memory limits; GDAL restricted to an allow-list of drivers (`GDAL_SKIP` and explicit driver lists) with network-backed virtual file systems disabled.
6. Store under a random name with checksum; original filename kept only as metadata.
7. ML artefacts are never accepted as uploads. Models are produced only by the platform's own training runs and verified by checksum before loading.

## 5. API security

- TLS everywhere (terminated at nginx or Caddy); HSTS.
- Security headers: Content-Security-Policy (self plus configured tile hosts), `X-Content-Type-Options`, `Referrer-Policy`, frame-ancestors none.
- CORS restricted to the configured frontend origin.
- CSRF: the refresh endpoint relies on `SameSite=Strict` plus an origin check; other endpoints use bearer tokens.
- Rate limiting at two layers: nginx `limit_req` per IP, and an application limiter per user and per organization (in-memory token bucket for a single node; PostgreSQL-backed counters when more than one API process is used). Stricter limits on auth, upload and job-creating endpoints.
- Job quotas per organization (concurrent Monte Carlo runs, training runs).
- Pagination caps; request body size caps; timeouts.
- Uniform error responses without stack traces; internal details only in logs with the request id.

## 6. Audit logging

Described in `docs/architecture.md` section 9. Additional security events logged: logins and failures, MFA changes, role and permission changes, exports and downloads (who took which data out), dataset and rule-pack imports, model promotions, scenario locks, report status changes, admin actions. The audit table is append-only and hash-chained; `GET /audit-logs/verify` recomputes the chain.

## 7. Sensitive industrial data protection

- Tenant isolation as above; file store paths are namespaced by organization and are never served directly, only through authorized endpoints.
- Encryption in transit: TLS for HTTP and for PostgreSQL connections when the database is on another host.
- Encryption at rest: full-disk or volume encryption on the host (LUKS, BitLocker); encrypted backups; column-level encryption (`pgcrypto` or application-side) for TOTP secrets and any stored third-party credentials.
- Confidentiality flags on materials and process parameters: fields marked confidential are masked for roles without `confidential.read` and are omitted or aggregated in reports generated for external audiences.
- Secrets: environment files readable only by the service account, or the OS secret store; never in the repository; rotation procedure documented.
- Data residency: single-tenant on-premises installation is a supported deployment, so data can stay inside the company network.
- Retention and deletion: organization export and deletion procedures; backups age out on a defined schedule.
- Personal data is minimal (name, email, activity logs); GDPR duties (records of processing, data subject requests) are covered in the operations manual.

## 8. Secure development

Dependency pinning with lock files (`uv.lock`, `pnpm-lock.yaml`); `pip-audit` and `pnpm audit` in CI; static analysis (`ruff` security rules, `bandit`); secret scanning; least-privilege database roles (migration role separate from runtime role); security tests in `docs/testing.md`; threat model reviewed in Phase 11 against the OWASP ASVS.
