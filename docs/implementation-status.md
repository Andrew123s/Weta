# Implementation status

Living record of what is built, against `docs/development-phases.md`. Updated at the end of every phase.

Last updated: 2026-10-05, end of Phase 1.

## 1. Phase summary

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | Architecture and scientific specification | Done, with one open gate | Docs exist and are internally consistent after the fixes in section 3. Open: the per-engine specialist review in the Phase 0 acceptance criteria is a human task and has not happened. It must be completed before engine results (Phase 4 onward) are used for any decision |
| 1 | Project foundation | Done locally; Linux CI not yet observed | See section 4 |
| 2 | Database and authentication | Not started | Blocked on a native PostgreSQL 16 + PostGIS 3.4 install (section 5) |
| 3 to 12 | | Not started | |

## 2. Repository inspection at the start of Phase 1

- Contents: `README.md`, `CLAUDE.md` and 21 documents in `docs/`. No source code, package configuration, environment configuration, database, migrations or tests existed.
- Version control: the folder sat inside an unrelated Git repository rooted at the user's home directory. A dedicated repository was initialised in the project folder, with remote `https://github.com/Andrew123s/Weta.git`. HTTPS is used because no SSH key is configured on this machine.

## 3. Architecture consistency review

All documents were read. The findings and how each was resolved:

| # | Finding | Resolution |
|---|---------|------------|
| 1 | `architecture.md` dependency rule 3 let `engines/scenarios` talk to `db`, contradicting rule 2 ("engines do not import db") and `CLAUDE.md` ("engines never touch the database"). `reporting` was likewise said to read stored results without saying how | Rule 3 clarified: only `apps/api` talks to `db`; the graph executor reaches stored runs through a `RunStore` protocol that `scenarios` defines and `apps/api` implements, and `reporting` receives results through a read protocol. Dependency direction is one-way and enforceable by `import-linter` |
| 2 | `architecture.md` section 4 said combining quantities "yields the weakest provenance class", but section 10 rule 2 says the output class comes from the node layer and inputs contribute taint flags | Section 4 aligned with section 10, which is the more precise rule and the one the UI and reports depend on |
| 3 | The `Quantity` sketch had no taint field, although taint flags must travel between nodes and appear in the API quantity object (`api.md`) | `taint` added to `Quantity`; documented in `architecture.md` section 4 |
| 4 | `Quantity.quality` was described as "pedigree-style indicators", while choosing a data-quality scheme is open decision D-09 | `quality` is scheme-neutral (`scheme`, `scheme_version`, `scores`); no indicator names are hard-coded |
| 5 | Phase diagram showed LCA (Phase 6) depending only on Phase 4; the phase table says Phases 4 and 5 | Diagram fixed |
| 6 | Development setup created only `postgis`, `pgcrypto` and `citext`; `data-model.md` also requires `pg_trgm` and `btree_gist` | Setup command fixed |
| 7 | Year length in unit conversions was unstated | Registered as assumption A-UNIT-01 (Julian year, 365.25 d) |

No other inconsistencies were found between the module layout, the API route map, the data model and the phase plan. The implementation brief's suggested engine list (`lca`, `risk`, `logistics`, `gis`, `ml`, `scenarios`, `waste`) is a subset of `architecture.md` section 12, which also has `fate`, `uncertainty`, `regulatory` and `reporting` as engines, with reasons given there. The docs are followed.

## 4. Phase 1: project foundation

### Delivered

| Item | Where |
|------|-------|
| uv workspace (Python 3.12), lock file | `pyproject.toml`, `uv.lock` |
| Core package: `Quantity` with unit, distribution, provenance, source, quality and taint; units via pint; seven distribution kinds with exact unit conversion; provenance classes, taint flags and combination rule; `@node` decorator, `NodeResult`, `NodeRegistry`; canonical JSON and input hashing; UUIDv7 | `packages/core/src/weta_core/` |
| Shared API contracts: RFC 9457 problem details, health, readiness and version responses, API quantity object | `packages/schemas/src/weta_schemas/` |
| API: app factory, settings from env, structured JSON logging with request id, request-id and security-header middleware, CORS, problem-details error handlers, `GET /api/v1/health`, `/health/ready` (database and PostGIS check), `/version`, OpenAPI at `/api/v1/openapi.json` | `apps/api/weta_api/` |
| Web: Vite + React 18 + strict TypeScript, router, shell with the 14 navigation areas, design tokens (light and dark), generated API types, `QuantityCell`, `ProvenanceBadge`, `TaintFlags`, uncertainty-driven number formatting, live dashboard of system status | `apps/web/` |
| Tooling: ruff (lint and format), mypy `--strict`, import-linter contracts, ESLint (strict type-checked), Prettier, Vitest, axe accessibility checks | config in `pyproject.toml`, `apps/web/` |
| CI on Ubuntu and Windows hosted VMs, no containers | `.github/workflows/ci.yml` |
| Dev scripts and env template | `scripts/dev.ps1`, `scripts/dev.sh`, `.env.example`, `scripts/export_openapi.py` |

### Behaviour worth knowing

- Arithmetic on a `Quantity` that carries a non-point distribution raises `UncertaintyPropagationError` rather than dropping the distribution. Arithmetic on an unavailable value raises `MissingValueError` rather than treating it as zero.
- The `@node` wrapper rejects any output quantity whose provenance class differs from the node's layer, so an ML node cannot emit a value that is not `PREDICTED`.
- `NodeResult` refuses an output with any status other than `ok`, refuses `insufficient_data` without the list of missing inputs, and requires a reason for `out_of_validity_range` and `not_applicable`.
- The input hash is stable across processes and platforms (tested with different `PYTHONHASHSEED` values; a golden hash computed independently with `hashlib` is checked on both CI operating systems).
- The readiness endpoint never returns the database URL or driver error text.

### Tests (local, Windows 11, 2026-10-05)

| Suite | Result |
|-------|--------|
| Python (`uv run pytest --cov`) | 171 passed; coverage 98.1 % (floor set at 90 %) |
| Import contracts (`uv run lint-imports`) | 3 kept, 0 broken |
| Ruff, mypy `--strict` | clean |
| Web (`pnpm --filter web test`) | 43 passed, including axe checks on every page shell |
| Web lint, type-check, production build | clean |
| Manual | API and web dev servers run together; the dashboard shows live readiness ("database: not configured") and component versions; placeholder and not-found pages render |

Reference values in the tests are independent of the code under test: unit definitions (SI, Celsius offset, Julian year), hand calculations (2 g/L × 3 m³ = 6 kg), hand-written canonical JSON, and SHA-256 computed directly with `hashlib`.

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| `uv run pytest` and `pnpm test` green on Windows and Linux | Windows: met. Linux: runs in CI; not yet observed, because the GitHub CLI is not authenticated on this machine |
| CI green | Pending first CI run on GitHub |
| Import contracts enforced | Met (`lint-imports` in CI) |
| No container files in the repository | Met, and enforced by `tests/test_repository_hygiene.py` |

### Deviations and decisions in Phase 1

- Dev dependency `httpx2` instead of `httpx`: Starlette 1.x deprecates `httpx` for its test client.
- TypeScript pinned to 5.9: typescript-eslint and openapi-typescript do not yet support TypeScript 7.
- The OpenAPI document publishes `QuantityOut` and `ProblemDetail` even though no Phase 1 route returns a quantity, so the generated TypeScript types include them (`docs/frontend.md`: API types are generated, not hand-written).
- Application rate limiting is not in Phase 1; `docs/security.md` places it with authentication (Phase 2) and finalizes it in Phase 11.
- Playwright end-to-end tests start in Phase 2 with the first real workflow (sign-in).

## 5. Environment and missing dependencies

| Dependency | State on the development machine | Needed from |
|------------|----------------------------------|-------------|
| uv 0.9, Python 3.12 (installed by uv) | Present | Phase 1 |
| Node.js 24, pnpm 10 | Present | Phase 1 |
| PostgreSQL 16 + PostGIS 3.4 (+ `pgcrypto`, `citext`, `pg_trgm`, `btree_gist`) | Not installed | Phase 2 |
| GitHub CLI authentication (to observe CI) | Not authenticated | Now |
| GeoPandas, Rasterio, Shapely, PyProj (binary wheels) | Not yet added | Phase 5 |
| pgRouting or an external router (decision D-05) | Not installed | Phase 5 |
| LightGBM, SHAP, SALib | Not yet added | Phases 8 and 9 |
| WeasyPrint with Pango/GTK runtime | Not installed | Phase 10 |
| Playwright browsers | Not installed | Phase 2 |

## 6. Next: Phase 2 (database and authentication)

Prerequisite: PostgreSQL 16 with PostGIS 3.4 installed natively (EDB installer and StackBuilder on Windows), roles `weta_migrate` and `weta_app`, and database `weta_dev`.

Scope from `docs/development-phases.md`: `packages/db` (identity, organizations, projects, datasets, source_refs, documents, audit_logs, jobs; repositories; Alembic), auth (Argon2id, JWT access token and rotating refresh cookie, TOTP), RBAC, row-level security, the hash-chained append-only audit log, the PostgreSQL job queue and worker, and the login, project and audit UI.
