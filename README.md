# Weta

Upstream industrial waste logistics: predictive EIA, LCA, GIS and machine learning platform.

Weta answers one question:

> Before an industrial production or waste-management change occurs, what environmental consequences could result, where could they occur, which environmental receptors are vulnerable, what uncertainty exists, and which alternative scenario provides the best environmental outcome?

The documents in `docs/` are the source of truth for implementation. Phase 1 (project foundation) is built: the core `Quantity`, units, provenance, node and hashing package, the API skeleton and the web shell. No environmental engine exists yet. Current state, test results and missing dependencies are in [docs/implementation-status.md](docs/implementation-status.md).

## Quick start (native, no containers)

Requires `uv` and Node.js with `pnpm` (see [docs/deployment.md](docs/deployment.md)). PostgreSQL + PostGIS is needed from Phase 2.

```
uv sync
pnpm install
cp .env.example .env            # optional in Phase 1; leave WETA_DATABASE_URL empty without a database
uv run pytest                   # Python tests
pnpm test                       # web tests
scripts/dev.sh                  # or: powershell -File scripts\dev.ps1  -> API :8000, web :5173
```

API documentation: http://localhost:8000/api/v1/docs (development only).

## Reading order

| # | Document | Purpose |
|---|----------|---------|
| 1 | [docs/architecture.md](docs/architecture.md) | System, component, backend, auth, audit and provenance architecture |
| 2 | [docs/data-model.md](docs/data-model.md) | PostgreSQL/PostGIS schema and ERD |
| 3 | [docs/environmental-models.md](docs/environmental-models.md) | The 14 engines: inputs, outputs, equations, limits |
| 4 | [docs/scenario-engine.md](docs/scenario-engine.md) | Calculation graph, incremental recalculation, comparison, decision support |
| 5 | [docs/lca.md](docs/lca.md) | LCI, characterization factors, LCIA, dataset providers |
| 6 | [docs/gis.md](docs/gis.md) | PostGIS layers, derived variables, raster pipeline |
| 7 | [docs/logistics.md](docs/logistics.md) | Waste logistics chain and transport risk |
| 8 | [docs/risk-engine.md](docs/risk-engine.md) | Groundwater, surface water, atmospheric, ecotoxicity, aggregation, uncertainty |
| 9 | [docs/ml.md](docs/ml.md) | ML tasks, registry, explainability, monitoring |
| 10 | [docs/regulatory-engine.md](docs/regulatory-engine.md) | Data-driven, jurisdiction-independent rules |
| 11 | [docs/reporting.md](docs/reporting.md) | Report assembly and exports |
| 12 | [docs/api.md](docs/api.md) | REST API structure |
| 13 | [docs/frontend.md](docs/frontend.md) | Frontend architecture and screens |
| 14 | [docs/security.md](docs/security.md) | Authentication, RBAC, data protection |
| 15 | [docs/testing.md](docs/testing.md) | Test architecture and verified reference cases |
| 16 | [docs/deployment.md](docs/deployment.md) | Native deployment (no containers) |
| 17 | [docs/data-sources.md](docs/data-sources.md) | Recognized external datasets and their licences |
| 18 | [docs/assumptions.md](docs/assumptions.md) | Assumption register and open scientific decisions |
| 19 | [docs/development-rules.md](docs/development-rules.md) | Binding rules for anyone (human or agent) writing code |
| 20 | [docs/development-phases.md](docs/development-phases.md) | Phases 0 to 12 with acceptance criteria |
| 21 | [docs/diagrams.md](docs/diagrams.md) | Index of every diagram |
| 22 | [docs/implementation-status.md](docs/implementation-status.md) | What is built, test results, open gates and missing dependencies |

## Stack

React + TypeScript + Vite, MapLibre GL JS, Python 3.12 + FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 16 + PostGIS 3.4, GeoPandas / Shapely / Rasterio / GDAL / PyProj, scikit-learn / LightGBM / SHAP, uv, pnpm, Pytest, Vitest, Playwright. Everything is installed natively. Containers are not used anywhere.

## Status of scientific content

The docs name recognized methods and databases and define how they plug in. They do not contain numeric characterization factors, chemical properties, emission factors or regulatory thresholds. Those values must be imported from their licensed or official sources through the provider layer. See `docs/data-sources.md`.
