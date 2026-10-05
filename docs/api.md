# API structure

REST, JSON, OpenAPI 3.1 at `/api/v1/openapi.json`. Base path `/api/v1`. All routes require authentication except `/auth/login`, `/auth/refresh`, `/health`.

## Conventions

- Resource naming: plural nouns, kebab-case. Nested only one level where ownership is strict.
- Pagination: cursor-based (`?limit=&cursor=`), response envelope `{ "items": [], "next_cursor": null }`.
- Filtering: explicit query parameters, no free-form query language.
- Errors: RFC 9457 problem details (`type`, `title`, `status`, `detail`, `errors[]`, `request_id`).
- Concurrency: `ETag` + `If-Match` on mutable resources.
- Idempotency: `Idempotency-Key` header on POST endpoints that enqueue jobs.
- Every numeric field is a quantity object:

```json
{
  "value": 12.4,
  "unit": "t/yr",
  "uncertainty": { "distribution": "triangular", "min": 10.1, "mode": 12.4, "max": 15.0 },
  "provenance": "DERIVED",
  "taint": { "predicted": false, "scenario_assumption": true, "synthetic": false, "user_provided": true },
  "source_ref": "018f...",
  "result_id": "018f..."
}
```

- Long operations return `202 Accepted` with `{ "job_id": ... }`.
- GeoJSON for geometry in bodies; vector tiles for map rendering.

## Route map

| Group | Routes |
|-------|--------|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/mfa/enroll`, `POST /auth/mfa/verify`, `POST /auth/password/change`, `POST /auth/password/reset-request`, `POST /auth/password/reset` |
| Identity | `GET /me`, `GET/POST /organizations/{id}/members`, `GET/POST/PATCH /roles`, `GET /permissions`, `GET/POST/DELETE /api-keys` |
| Projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `GET/POST /projects/{id}/members`, `GET/POST /projects/{id}/facilities` |
| Facilities | `GET/POST /facilities`, `GET/PATCH /facilities/{id}`, `GET/POST /facilities/{id}/locations`, `/storage-units`, `/emission-points` |
| Production | `GET/POST /facilities/{id}/processes`, `GET/PATCH /processes/{id}`, `/processes/{id}/steps`, `/steps/{id}/inputs`, `/steps/{id}/parameters`, `/steps/{id}/transfer-coefficients`, `/processes/{id}/production-records`, `/processes/{id}/consumption-records` |
| Materials | `GET/POST /materials`, `/materials/{id}/composition`, `GET /chemicals?cas=&q=`, `GET /chemicals/{id}`, `GET /chemicals/{id}/properties`, `POST /chemicals/{id}/properties` (user-provided, with source), `GET /chemicals/{id}/hazards` |
| Waste | `GET/POST /waste-streams`, `/waste-streams/{id}/composition`, `/generation-records`, `/hazards`, `GET /waste-codes?scheme=`, `GET/POST /emissions`, `GET/POST /wastewater` |
| Logistics | `GET/POST /treatment-facilities`, `/disposal-facilities`, `/transfer-stations`, `/vehicles`, `GET/POST /waste-streams/{id}/logistics-chains`, `/logistics-chains/{id}/legs`, `POST /routes/compute` (job), `GET /routes/{id}`, `GET/POST /transport-events` |
| GIS | `GET /layers`, `GET /layers/{id}`, `GET /tiles/{layer}/{z}/{x}/{y}.mvt`, `GET /raster-tiles/{layer}/{z}/{x}/{y}.png`, `GET/POST /projects/{id}/receptors`, `POST /gis/derive` (job), `GET /derived-variables?subject=`, `POST /gis/query/proximity`, `POST /gis/query/buffer-summary` |
| Data | `GET/POST /datasets`, `POST /datasets/{id}/versions` (upload, job), `GET /dataset-versions/{id}`, `GET/POST /documents`, `GET /providers`, `POST /providers/{code}/import` (job) |
| Scenarios | `GET/POST /projects/{id}/scenarios`, `POST /scenarios/{id}/duplicate`, `GET/PATCH /scenarios/{id}`, `GET/POST/DELETE /scenarios/{id}/inputs`, `POST /scenarios/{id}/run` (job), `GET /scenarios/{id}/graph` (nodes, status, staleness), `GET /scenarios/{id}/results?output=&subject=`, `POST /scenarios/{id}/lock`, `POST /scenarios/combine` |
| Comparison | `POST /comparisons` (baseline + alternatives, returns absolute and percent deltas with intervals), `POST /decision-analyses` (objectives, weights, method), `GET /decision-analyses/{id}` |
| LCA | `GET/POST /projects/{id}/lca-goal-scopes`, `GET /lcia-methods`, `GET /impact-categories?method_version=`, `GET/POST /lci-activity-links`, `GET /lci-processes?q=`, `GET /scenarios/{id}/lca` (inventory and impact separately), `GET /scenarios/{id}/lca/contributions` |
| Risk | `GET /scenarios/{id}/risk-assessments?pathway=`, `GET /risk-assessments/{id}`, `GET/POST /risk-matrices` |
| Uncertainty | `POST /scenarios/{id}/uncertainty-analyses` (job), `GET /uncertainty-analyses/{id}`, `POST /scenarios/{id}/sensitivity-analyses` (job), `GET /sensitivity-analyses/{id}` |
| ML | `GET/POST /ml/models`, `POST /ml/models/{id}/training-runs` (job), `GET /ml/training-runs/{id}`, `GET /ml/model-versions/{id}` (model card), `POST /ml/model-versions/{id}/transition`, `POST /ml/model-versions/{id}/predict`, `GET /ml/predictions/{id}/explanation`, `GET /ml/model-versions/{id}/monitoring` |
| Regulatory | `GET /jurisdictions`, `GET /regulations`, `GET /regulatory-rules?jurisdiction=&category=&on_date=`, `POST /rule-packs/import` (job), `GET /scenarios/{id}/regulatory-evaluations` |
| Reports | `GET/POST /projects/{id}/reports`, `POST /reports/{id}/build` (job), `GET /reports/{id}`, `GET /reports/{id}/exports/{format}`, `GET/POST /report-templates` |
| Traceability | `GET /results/{id}`, `GET /results/{id}/trace?depth=`, `GET /runs/{id}`, `GET /assumptions`, `GET /method-versions` |
| Audit | `GET /audit-logs?entity=&actor=&from=&to=`, `GET /audit-logs/verify` (hash chain check) |
| Jobs | `GET /jobs/{id}`, `POST /jobs/{id}/cancel`, `GET /jobs/{id}/events` (SSE) |
| System | `GET /health`, `GET /version` |

## Example: scenario lifecycle

```mermaid
sequenceDiagram
  participant U as User
  participant A as API
  participant Q as jobs table
  participant W as Worker
  participant E as Graph executor + engines
  participant D as PostgreSQL
  U->>A: POST /scenarios/{baseline}/duplicate
  A->>D: insert scenario (parent = baseline)
  U->>A: POST /scenarios/{s}/inputs (replace solvent A by B, rationale)
  A->>D: insert scenario_inputs; mark affected nodes stale
  U->>A: POST /scenarios/{s}/run
  A->>Q: enqueue scenario.run
  A-->>U: 202 job_id
  W->>Q: claim job
  W->>E: resolve state = baseline + overrides
  E->>D: look up input_hash for each node
  E->>E: execute only nodes with new hashes
  E->>D: insert calculation_runs, inputs, result_values
  W->>Q: job done
  U->>A: POST /comparisons {baseline, [s]}
  A-->>U: deltas (absolute, percent, intervals), per dimension
```
