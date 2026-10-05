# Assumptions register

Every assumption used by an engine is registered here and in the `assumptions` table with the same code. A run records which assumptions it used and with what value (`run_assumptions`). Nothing in this register is a hidden constant: values marked "configured" have no default in code and must be set, with a source or rationale, before the node will run.

## 1. Platform-level

| Code | Assumption | Consequence if wrong |
|------|------------|----------------------|
| A-GEN-01 | Built-in environmental models are screening tier | Over- or under-statement at specific sites; refined models needed for decisions on individual receptors |
| A-GEN-02 | Missing data is reported as a gap and is never replaced with a default unless a registered assumption is explicitly enabled | More "not assessed" results; fewer false assurances |
| A-GEN-03 | Baseline period is representative of normal operation | Scenario deltas inherit baseline bias |
| A-GEN-04 | Input distributions are independent unless a correlation is declared | Uncertainty may be under- or over-stated |
| A-GEN-05 | Regulatory evaluation is decision support, not legal advice | n/a |
| A-UNIT-01 | In unit conversions, a year (`yr`, `a`) is the Julian year of 365.25 days (the `pint` definition, `packages/core/src/weta_core/units.py`). A source that reports annual totals over calendar years of 365 or 366 days is converted with this definition | Per-second or per-day rates derived from annual totals differ by up to about 0.27 % from a calendar-year basis; negligible against typical inventory uncertainty, but visible in exact reproductions |

## 2. Engine-level

| Code | Engine | Assumption | Value |
|------|--------|------------|-------|
| A-MB-01 | Material balance | Steady state over the period | structural |
| A-MB-02 | Material balance | Transfer coefficients independent of throughput within validity range | structural; range configured per coefficient |
| A-MB-03 | Material balance | On substitution, inherited transfer coefficients are provisional | flagged per override |
| A-MB-04 | Material balance | Mass-closure tolerance before a warning | configured |
| A-WG-01 | Waste generation | Tier 2 scales linearly with production | structural |
| A-WC-01 | Characterization | Homogeneous composition | structural |
| A-WC-02 | Characterization | Maximum unspecified fraction for a non-hazardous conclusion | configured |
| A-LG-01 | Logistics | Representative route for all trips | structural |
| A-LG-02 | Logistics | Empty-return fraction | configured |
| A-LG-03 | Logistics | Corridor half-width per hazard class | configured, with source |
| A-LG-04 | Logistics | Incident rate depends on road class only | structural |
| A-FT-01 | Fate | Linear equilibrium sorption, Kd = Koc * f_oc for neutral organics | structural |
| A-FT-02 | Fate | First-order degradation | structural |
| A-GW-01 | Groundwater | Homogeneous isotropic porous medium, uniform steady flow | structural |
| A-GW-02 | Groundwater | Piston flow, no dispersion | structural |
| A-GW-03 | Groundwater | Unknown gradient direction: all receptors in radius treated as potentially down-gradient | structural |
| A-GW-04 | Groundwater | Receptor search radius | configured |
| A-GW-05 | Groundwater | Assessment time horizon | configured |
| A-SW-01 | Surface water | Complete mixing, no in-stream attenuation (first tier) | structural |
| A-SW-02 | Surface water | Low-flow statistic used for the conservative case | configured by jurisdiction profile |
| A-AT-01 | Atmospheric | Screening plume: flat terrain, steady state, no deposition or chemistry | structural |
| A-AT-02 | Atmospheric | Meteorological matrix for worst-case screening | configured from the chosen published scheme |
| A-EC-01 | Ecotoxicity | Concentration addition for mixtures (first tier) | structural |
| A-EC-02 | Ecotoxicity | Substances without PNEC are "not assessed" | structural |
| A-VU-01 | Vulnerability | Buffer radii per receptor type | configured |
| A-VU-02 | Vulnerability | Index weights from the selected scheme | imported or organization-defined with rationale |
| A-RA-01 | Aggregation | Risk matrix class boundaries | configured, versioned |
| A-LCA-01 | LCA | Boundary, functional unit, multifunctionality rule as in goal and scope | per assessment |
| A-LCA-02 | LCA | Proxy processes where no exact match | per link, flagged |
| A-UN-01 | Uncertainty | Sample cap and convergence tolerance | configured |
| A-ML-01 | ML | Minimum observations per task for training | configured in Phase 9 from learning curves |
| A-ML-02 | ML | Future resembles the training period within the applicability domain | structural |

## 3. Open scientific decisions (to be resolved in the phase shown)

| Id | Decision | Phase |
|----|----------|-------|
| D-01 | Which groundwater vulnerability scheme is the default per region (imported map vs DRASTIC vs GOD) | 7 |
| D-02 | Stability-class and dispersion-coefficient scheme for the screening plume | 7 |
| D-03 | LCA backend: in-house solver vs Brightway wrapper | 6 |
| D-04 | Default LCIA method per jurisdiction profile | 6 |
| D-05 | Routing provider (pgRouting vs external router) | 5 |
| D-06 | Source of transport incident rates per jurisdiction | 5 |
| D-07 | Default risk matrix definition and wording of classes | 7 |
| D-08 | ML minimum-data gates | 9 |
| D-09 | Which pedigree-style data-quality scheme (if any) to import for default uncertainty | 6 |

Each decision is closed with an ADR in `docs/adr/` reviewed by a domain specialist.

## 4. Review

Scientific content of the engine documents should be reviewed by qualified specialists (hydrogeology, air quality, LCA, ecotoxicology, waste law) before Phase 7 results are used for any real decision. The architecture makes that review practical by giving every method a version, a document anchor and reference cases.
