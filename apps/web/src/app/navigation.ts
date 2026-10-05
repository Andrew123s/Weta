/**
 * Main navigation (docs/frontend.md section 3). `phase` is the development phase in
 * docs/development-phases.md that delivers the area; until then the page says so plainly.
 */
export interface NavItem {
  path: string;
  label: string;
  phase: number;
  summary: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    path: "/",
    label: "Dashboard",
    phase: 1,
    summary: "Project status, data completeness, open data gaps, recent jobs and regulatory flags.",
  },
  {
    path: "/projects",
    label: "Projects",
    phase: 2,
    summary: "Create and configure projects: jurisdiction, working CRS, members, baseline period.",
  },
  {
    path: "/facilities",
    label: "Facilities",
    phase: 3,
    summary: "Facility master data, location, storage units, emission points and documents.",
  },
  {
    path: "/production",
    label: "Production",
    phase: 3,
    summary: "Process steps, bill of materials, parameters, transfer coefficients and records.",
  },
  {
    path: "/materials",
    label: "Materials",
    phase: 3,
    summary: "Materials, compositions, chemicals by CAS number, properties with all sources.",
  },
  {
    path: "/waste",
    label: "Waste",
    phase: 3,
    summary: "Waste streams, generation records, composition, classification and emissions.",
  },
  {
    path: "/gis",
    label: "GIS",
    phase: 5,
    summary: "Map with source layers, derived variables, receptors, routes and scenario layers.",
  },
  {
    path: "/scenarios",
    label: "Scenarios",
    phase: 8,
    summary: "Overrides with rationale, affected-node preview, runs, comparison, decision support.",
  },
  {
    path: "/lca",
    label: "LCA",
    phase: 6,
    summary: "Goal and scope, activity mapping, inventory, impacts, contributions.",
  },
  {
    path: "/risk",
    label: "Risk",
    phase: 7,
    summary: "Risk profile by pathway and receptor, linkage table and pathway detail.",
  },
  {
    path: "/ml",
    label: "ML",
    phase: 9,
    summary: "Model registry, model cards, training with data gates, predictions, explanations.",
  },
  {
    path: "/reports",
    label: "Reports",
    phase: 10,
    summary: "Templates, pre-flight checks, builds, exports, approval and snapshot hashes.",
  },
  {
    path: "/data",
    label: "Data",
    phase: 3,
    summary: "Datasets and versions, import wizard, documents, providers, assumption register.",
  },
  {
    path: "/admin",
    label: "Administration",
    phase: 2,
    summary: "Users, roles, API keys, rule packs, audit log with chain verification, jobs.",
  },
];
