# CLAUDE.md

Instructions for Claude Code working in this repository.

1. `docs/` is the source of truth. Read `docs/development-rules.md` before writing any code, and the doc for the subsystem you are touching.
2. Work one phase at a time, following `docs/development-phases.md`. Do not start a phase until the previous phase meets its acceptance criteria.
3. If code and docs disagree, stop and fix the doc first (with a note in `docs/assumptions.md` if the change is scientific), then the code.
4. Hard rules (full list in `docs/development-rules.md`):
   - No Docker, no containers, no Kubernetes. Native installs only.
   - Never invent a chemical property, emission factor, characterization factor, regulatory threshold, dataset or model metric. If a value is missing, the engine returns `status = "insufficient_data"` with the list of missing inputs.
   - Every numeric value crossing an engine boundary is a `Quantity` (value, unit, uncertainty, provenance class, source).
   - Every engine is a pure function registered as a node in the calculation graph. Engines never touch the database or HTTP.
   - ML never replaces a deterministic model where one exists. ML outputs are always tagged `PREDICTED`.
   - One engine per concern. Do not duplicate logic across engines or services.
   - Every calculation has a test with an independently verified expected value.
5. Sample data lives in `data/sample/` and is always tagged `SYNTHETIC_DEMO`. It must never be presented as real.
6. Commands (once Phase 1 exists): `uv sync`, `uv run pytest`, `uv run alembic upgrade head`, `uv run uvicorn weta_api.main:app --reload`, `pnpm --filter web dev`.
