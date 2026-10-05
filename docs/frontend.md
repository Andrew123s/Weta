# Frontend architecture

React 18 + TypeScript (strict) + Vite. A dense, professional working tool. Function before decoration: tables, maps, forms and charts that expose provenance, uncertainty and lineage everywhere.

## 1. Structure

```
apps/web/src/
  app/            router, providers, layout shell, error boundaries
  api/            generated OpenAPI types + thin typed client, TanStack Query hooks
  features/
    dashboard/ projects/ facilities/ production/ materials/ waste/
    gis/ scenarios/ lca/ risk/ ml/ reports/ data/ admin/
  components/
    quantity/     QuantityCell, QuantityInput, UnitSelect, IntervalBar
    provenance/   ProvenanceBadge, TaintFlags, SourcePopover
    trace/        TracePanel (lineage tree), MethodInfo
    status/       ResultStatus (ok, insufficient data, out of range, blocked, stale)
    charts/       Tornado, IntervalPlot, Waterfall, ParallelCoordinates, StackedStage, Sankey
    map/          MapView, LayerTree, Legend, FeaturePopup, DrawTools
    tables/       DataTable (virtualized, column units, export)
  lib/            formatting (significant figures by uncertainty), units, permissions
  styles/         design tokens (from the Weta design system), base CSS
```

- Server state: TanStack Query (caching, invalidation by scenario and node). UI state: Zustand (selected scenario, map view, panel layout). No global store holding server data.
- Routing: React Router with project-scoped routes `/p/:projectId/...` and a persistent scenario selector in the shell.
- Forms: React Hook Form + Zod schemas derived from the OpenAPI types.
- Permissions: a `can(permission)` helper from `/me`; controls are hidden or disabled with a reason. The server remains the authority.
- Internationalization scaffolded from the start (English first; German next); numbers and dates through `Intl`.
- Accessibility: WCAG 2.1 AA, keyboard-operable tables and trees, map features also available as a table, colour never the only signal.

## 2. Cross-cutting UI contracts

1. **Quantity display.** Value with significant figures set by its uncertainty, unit, interval bar or range text, provenance badge, and a click target that opens the trace panel. A bare number without unit and provenance is a bug.
2. **Provenance badges.** Eight classes, each with a text code, a shape and a colour: OBS, USR, IMP, DER, MOD, PRED, ASM, DEMO. Taint flags (built on predicted, assumption, synthetic inputs) appear as small markers beside the badge.
3. **Result status.** `insufficient_data` shows a "what is missing" list that links to the right form. `stale` shows what changed. `blocked` names the upstream node.
4. **Tier label.** Screening results are always labelled as screening, with the scope statement one click away.
5. **Trace panel.** A side panel showing the lineage tree of any result: node and method version, inputs with their provenance, dataset versions, assumptions, user and time, link to the method document.
6. **Scenario context.** Every page shows which scenario is displayed. Overridden fields are marked, with baseline value on hover.
7. **Observed and predicted are separated visually** in every chart (solid vs dashed, filled vs hollow markers) with a legend.

## 3. Pages

| Area | Content |
|------|---------|
| Dashboard | Project list with status; for a project: scenario status (up to date, stale, running), data completeness by domain, open data gaps ranked by sensitivity, recent jobs, regulatory flags. No vanity charts |
| Projects | Create and configure: jurisdiction, working CRS, members, goal and scope, baseline period |
| Facilities | Master data, location on map, storage units, emission points, documents |
| Production | Process editor (ordered steps), bill of materials per step, parameters, transfer coefficients, production and consumption records; mass-balance view as a Sankey diagram with closure indicator |
| Materials | Materials and compositions; chemical lookup by CAS; property table per chemical showing all sources and the selected value; hazard classifications; missing-property list |
| Waste | Streams, generation records, composition, classification result with triggering rule and substance, treatment compatibility, emissions and wastewater |
| GIS | Full-screen map: layer tree grouped as Source data / Derived variables / Model outputs, receptor management, buffer and proximity tools, route display with per-segment exposure, scenario difference layer, dataset date and coverage in the legend |
| Scenarios | List and tree of scenarios; override editor with rationale; substitution checklist; affected-node preview; run and progress; calculation-graph view with node status; comparison view (delta table, absolute and percent, intervals, class changes, "why it changed" path); decision support (performance matrix, Pareto flags, weights panel, robustness) |
| LCA | Goal and scope; activity-to-process mapping with match quality; inventory explorer; impact results by category and stage; contribution analysis; uncharacterized flows; method and dataset versions |
| Risk | Risk profile matrix (pathway by receptor type) with completeness; linkage table; detail pages per pathway with inputs, intermediate values, limitations; risk matrix definition; map link |
| ML | Model registry; model cards with stored metrics, baseline comparison, applicability domain; training-run launcher with data gate feedback; predictions with intervals and domain flags; explanations (waterfall, global importance, scenario comparison) with the non-causality notice; monitoring charts |
| Reports | Template selection, section configuration, pre-flight checks, build progress, exports, approval workflow, snapshot hash |
| Data | Datasets and versions, import wizard with validation report, documents, provider status, units, assumption register, method versions |
| Administration | Users, roles, permissions, API keys, rule packs, jurisdictions, audit log viewer with chain verification, job monitor, system settings |

## 4. Map architecture

MapLibre GL JS. Vector tiles from the API for large layers; GeoJSON for small project layers (receptors, facilities, routes) so they can be edited. Raster tiles from the COG tile router. Styling from the design tokens; sequential palettes for ordered classes, a diverging palette for scenario differences, hatching or patterns in addition to colour for hazard and protection zones. Drawing with a maintained draw plugin (for example Terra Draw). Map state (centre, zoom, visible layers, selected scenario) is encoded in the URL so a view can be shared and cited.

## 5. Performance

Route-level code splitting (the map and chart libraries load on demand); virtualized tables; query-level caching keyed by scenario and result hash (results are immutable, so they cache indefinitely); server-side aggregation for large tables; no client-side recomputation of scientific values, ever. The browser only formats and displays.

## 6. Visual design

Tokens (colour, type, spacing, radius, provenance colours) are defined in the Weta design system and imported as CSS variables. Light and dark themes. Restrained palette: neutral surfaces, one accent, semantic colours reserved for status and provenance.
