# Development rules

These rules are binding. A pull request that breaks one is rejected regardless of other merit.

## A. Absolute rules

1. No Docker, Docker Compose, Kubernetes or any container runtime, in development, CI, or production. Services are installed natively.
2. Do not invent environmental datasets, chemical properties, emission factors, LCA characterization factors, regulatory thresholds, model accuracy figures or environmental predictions. Numbers of these kinds enter the system only through an importer in `packages/providers` with a `dataset_version`, or through user entry with provenance.
3. No unexplained score. Any aggregate is stored together with its components, weights, normalization references and method version, and the UI must let the user open it up.
4. Assumptions are registered in `assumptions` (database) and `docs/assumptions.md`, and each run records the assumptions it used.
5. Uncertainty is preserved. Do not collapse a distribution or range to a point before the final presentation step, and present the range there too.
6. Observed data and predictions are stored in different tables and displayed with different provenance badges.
7. Where a transparent deterministic model exists and has its required inputs, use it. ML is for gaps the deterministic chain cannot fill, and for anomaly detection and forecasting.
8. No country-specific logic in engine code. Jurisdiction lives in rule packs and provider configuration.
9. One engine per concern. No duplicate services, no duplicate calculations. If two places need the same number, they read the same node output.
10. Modular monolith. No new network service without an architecture decision record in `docs/adr/`.
11. Every calculation is testable in isolation and has at least one reference case with an independently verified expected value.
12. Every result is traceable through `calculation_run_inputs`.
13. Every dataset has a `dataset_version` with publisher, licence, retrieval date and checksum.
14. Every model, method and rule is versioned (semver). Changing behaviour without bumping the version is forbidden.

## B. Engine rules

1. Engines are pure. No database, file, network, clock or global random state. Inputs in, outputs out.
2. All numeric inputs and outputs are `Quantity`. Unit conversion happens only through `packages/core/units`.
3. Each node declares: id, version, layer, input model, output model, method reference (doc anchor), validity range.
4. Outside the validity range the node returns `out_of_validity_range` and does not extrapolate silently.
5. Missing inputs give `insufficient_data` with the missing field list. Never substitute a default unless it is a registered assumption, and then record it in `assumptions_used`.
6. Screening models say they are screening models in their output (`tier = "screening"`) and in every label that reaches the user.
7. Equations in code carry a comment citing the doc anchor and the published source.

## C. Data rules

1. Migrations only through Alembic. No manual schema edits.
2. No giant JSON state. JSONB only for the cases listed in `docs/data-model.md`.
3. Sample data is `SYNTHETIC_DEMO`, lives in `data/sample/`, and is loaded only by `scripts/load_demo.py`.
4. Proprietary datasets (for example licensed LCI databases) are never committed to the repository.

## D. Code rules

- Python 3.12, `uv` workspace, `ruff` (lint + format), `mypy --strict` on `packages/core`, `packages/schemas` and all engines.
- TypeScript strict mode, ESLint, Prettier. API types are generated, not hand-written.
- `import-linter` contracts enforce the dependency rules in `docs/architecture.md`.
- Conventional commits. One logical change per pull request. Scientific changes update the relevant doc in the same pull request.
- Public functions have docstrings stating units.
- No secrets in the repository. Configuration through environment files outside version control.
- Logging is structured JSON with `request_id`; never log passwords, tokens, or full uploaded file contents.

## E. Definition of done

A feature is done when: code is merged, unit and reference-case tests pass, the API is in OpenAPI, provenance badges render for every new value, the trace endpoint resolves every new result back to sources, the doc is updated, and the phase acceptance criteria that apply are met.
