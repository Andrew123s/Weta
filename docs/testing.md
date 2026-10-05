# Testing architecture

Tools: Pytest (+ Hypothesis, pytest-asyncio), Vitest + React Testing Library, Playwright. A native PostgreSQL + PostGIS instance is required for integration tests (a dedicated `weta_test` database, created from a template database per test session; each test runs in a transaction that is rolled back).

## 1. Test layers

| Layer | Scope | Location | Runs |
|-------|-------|----------|------|
| Unit | Pure functions: engines, units, hashing, rule evaluator | `engines/*/tests`, `packages/*/tests` | Every commit |
| Reference cases | Engine outputs against independently verified values | `tests/reference_cases/` | Every commit |
| Property-based | Invariants (mass conservation, monotonicity, unit round trips) | with unit tests | Every commit |
| Integration | Database, repositories, RLS, PostGIS queries, job queue, API | `tests/integration/` | Every commit |
| Contract | OpenAPI schema stability; generated TS types compile | CI step | Every commit |
| Frontend unit / component | Components, hooks, formatting of quantities and provenance | `apps/web/src/**/*.test.tsx` | Every commit |
| End-to-end | Full workflows in a browser | `tests/e2e/` | Before merge to main, nightly |
| Performance | Graph execution, Monte Carlo, tile serving, large imports | `tests/perf/` | Nightly |
| Security | Authn, authz, tenant isolation, upload abuse | `tests/security/` | Before merge to main |

## 2. Environmental calculations: independently verified reference cases

Each case is a YAML file:

```yaml
id: gw-traveltime-001
node: risk.groundwater.travel_time
node_version: "1.0.0"
source:
  kind: hand_calculation | published_example | external_tool
  citation: "<publication, page / tool and version>"
  verified_by: "<name>"
  verified_on: "<date>"
inputs: { ... quantities with units ... }
expected: { ... quantities with units ... }
tolerance: { relative: 1.0e-6 }
```

Rules:

- The expected value is produced by someone or something other than the code under test: a hand calculation in a reviewed worksheet stored beside the case, a worked example from a cited publication, or an established external tool (for example openLCA or Brightway for LCA, QGIS for spatial operations, the regulatory model's own test cases for dispersion adapters).
- A node cannot be released (`method_versions.status = released`) without at least one reference case per calculation branch.
- Changing an expected value requires a reviewer and a note explaining why the earlier value was wrong.
- Input values in reference cases that are not from a publication are synthetic and labelled so. They test arithmetic, not environmental truth.

Engine-specific checks:

| Engine | Tests |
|--------|-------|
| Material balance | Closure equals zero for consistent inputs; Hypothesis: total mass out equals total in for any valid coefficient set; reaction stoichiometry cases |
| Waste generation | Tier selection logic; linear scaling; downgrade when overrides touch upstream steps |
| Characterization | Rule evaluator on synthetic rule sets: single-substance limit, additive rule, cut-off; unspecified-fraction blocking |
| Logistics | Trips, tonne-km, empty returns; double-counting guard with LCA; "not quantified" when no incident-rate source |
| Fate | Kd, R, decay; validity-range refusal for ionizable substances |
| Groundwater | Travel times; DAF published example; unknown-gradient behaviour; refusal in karst flag |
| Surface water | Mixing mass balance; missing-flow behaviour |
| Atmospheric | Plume hand calculation; symmetry and monotonic decay with crosswind distance; adapter contract tests with a fake model |
| Ecotoxicity | RQ; mixture sum; not-assessed never counted as zero |
| LCA | Hand-solved 2x2 and 3x3 systems; reproduction of dataset publisher scores; uncharacterized-flow reporting |
| Vulnerability | Published scheme worked example; ordinal-only handling |
| Aggregation | Matrix lookup; completeness metric; missing data never lowers risk |
| Uncertainty | Sampler reproducibility by seed; known analytic distributions (sum of normals, product of lognormals) recovered within tolerance; convergence stop rule |
| Sensitivity | Standard test functions with known Sobol indices (for example Ishigami) |
| Units | Round-trip conversions; dimensional errors raised |

## 3. Database

Migrations apply from empty and from the previous release; downgrade of the latest migration; constraint tests (composition sums, immutability triggers, exclusion constraints, append-only tables); RLS tests that a session scoped to organization A cannot read or write organization B rows in every tenant table (generated automatically from metadata so new tables cannot be forgotten).

## 4. API

Per route: success, validation failure, unauthenticated, unauthorized, cross-tenant access, pagination, idempotency key behaviour, ETag conflicts. OpenAPI snapshot test to catch accidental breaking changes. Schemathesis fuzzing against the OpenAPI document.

## 5. GIS

Synthetic geometries with analytic answers (points on a known grid, squares of known area, a line crossing a polygon at known lengths); CRS handling including the antimeridian and high latitudes; invalid-geometry repair; raster zonal statistics on small arrays with known sums; nodata handling; tile endpoint returns valid MVT; staleness propagation when a dataset version is activated.

## 6. Machine learning

| Aspect | Test |
|--------|------|
| Preprocessing | Pipeline fit on train only; transform is deterministic; unseen categories and missing values handled as specified |
| Leakage prevention | Splitter never places later timestamps in train than in test; lag features use only past rows (checked by injecting a future-only signal and asserting the model cannot learn it); a target-shuffling test yields baseline-level performance |
| Dataset builder | Excludes PREDICTED, SCENARIO_ASSUMPTION and SYNTHETIC_DEMO rows from production training sets |
| Reproducibility | Same snapshot, seed and library versions give identical metrics and identical artefact predictions |
| Model loading | Checksum verified; wrong checksum refused; version mismatch warning |
| Inference | Schema contract; out-of-domain flag raised for inputs outside training ranges; interval contains point prediction |
| Explainability | SHAP additivity within tolerance; stable feature ordering; explanation stored for every prediction |
| Registry | Single production version; promotion requires permission; metrics shown equal metrics stored |
| Minimum data gate | Training refused below the configured gate |

Tests run on small synthetic datasets with planted structure. They verify the machinery. They are not evidence of real-world model accuracy.

## 7. Scenario engine

Override application for each op; combined-scenario conflict detection; hash stability (same inputs, same hash across processes and platforms); incremental recalculation (changing a route re-executes only the expected node set, asserted by node ids); early cut-off; blocked-node propagation; comparison arithmetic including zero baselines; paired-sample comparison; decision analysis (dominance on constructed matrices, weighted-sum and TOPSIS against hand calculations, constraint exclusion).

## 8. Reports

Golden-file tests of the report model JSON; PDF builds without error and contains required sections, provenance columns and watermark when synthetic; Excel sheets and data dictionary present; CSV and JSON agree with the report model; final status blocked by taints or unlocked scenarios; regeneration from snapshot gives identical content hashes.

## 9. Authentication and security

Password hashing parameters; lockout; refresh rotation and reuse detection; MFA flows; permission matrix (role by route, generated); IDOR probes; rate limits; upload abuse corpus (zip bomb, path traversal, polyglot files, oversize geometry); formula injection in exports; audit hash-chain verification detects a tampered row.

## 10. Frontend

Component tests for quantity display (value, unit, interval, provenance badge), forms with unit selection, scenario diff views, accessibility checks (axe) on each page shell. Map logic tested through a thin adapter with MapLibre mocked; visual map checks happen in Playwright.

## 11. End-to-end workflows (Playwright)

1. Sign in, create project, add facility and process, enter materials and production, see mass balance.
2. Import a spatial layer, add receptors, compute derived variables, view on map.
3. Define logistics chain, compute route, see exposure indicators.
4. Duplicate baseline, replace a solvent, complete the substitution checklist, preview affected nodes, run, compare with baseline.
5. Run Monte Carlo and sensitivity, view intervals and tornado chart.
6. Train a demo model on synthetic data, see model card flagged as demo, view an explanation.
7. Build a report, export PDF, Excel, CSV, JSON; open a result trace from a report reference.
8. Role checks: viewer cannot run; reviewer can lock and approve.

## 12. CI without containers

A CI runner (self-hosted or hosted virtual machine) with PostgreSQL and PostGIS installed natively from distribution packages, `uv` and `pnpm` caches, and Playwright browsers. The pipeline: lint and type-check, unit and reference cases, integration, frontend tests, build, end-to-end. Coverage thresholds: engines and core at a high bar (set in Phase 1 and ratcheted upward), other code at a moderate bar; coverage is a floor, reference cases are the real quality gate.
