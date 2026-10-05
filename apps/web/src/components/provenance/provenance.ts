/**
 * Provenance badge vocabulary (docs/frontend.md section 2, contract 2): each class has a
 * text code, a shape and a colour token, so colour is never the only signal.
 */
import type { ProvenanceClass, Taint } from "../../api/client";

export type BadgeShape =
  "disc" | "ring" | "square" | "diamond" | "triangle" | "dashed-ring" | "hexagon" | "cross";

export interface ProvenanceMeta {
  code: string;
  label: string;
  description: string;
  shape: BadgeShape;
  /** CSS custom property defined in styles/tokens.css. */
  colorVar: string;
}

export const PROVENANCE: Record<ProvenanceClass, ProvenanceMeta> = {
  OBSERVED: {
    code: "OBS",
    label: "Observed",
    description: "Measured at the facility or in the field, with a measurement record",
    shape: "disc",
    colorVar: "--prov-observed",
  },
  USER_PROVIDED: {
    code: "USR",
    label: "User-provided",
    description: "Entered by a user without a measurement record",
    shape: "ring",
    colorVar: "--prov-user",
  },
  IMPORTED: {
    code: "IMP",
    label: "Imported",
    description: "Loaded from an external dataset with a recorded dataset version",
    shape: "square",
    colorVar: "--prov-imported",
  },
  DERIVED: {
    code: "DER",
    label: "Derived",
    description: "Deterministic calculation or GIS operation on other data",
    shape: "diamond",
    colorVar: "--prov-derived",
  },
  MODELLED: {
    code: "MOD",
    label: "Modelled",
    description: "Output of an environmental model with stated assumptions",
    shape: "triangle",
    colorVar: "--prov-modelled",
  },
  PREDICTED: {
    code: "PRED",
    label: "Predicted",
    description: "Output of a statistical or machine-learning model",
    shape: "dashed-ring",
    colorVar: "--prov-predicted",
  },
  SCENARIO_ASSUMPTION: {
    code: "ASM",
    label: "Scenario assumption",
    description: "Value set by a user as a what-if",
    shape: "hexagon",
    colorVar: "--prov-assumption",
  },
  SYNTHETIC_DEMO: {
    code: "DEMO",
    label: "Synthetic demonstration data",
    description: "Fabricated for demonstration and tests only; never real environmental data",
    shape: "cross",
    colorVar: "--prov-demo",
  },
};

export interface TaintMeta {
  key: keyof Taint;
  code: string;
  label: string;
}

export const TAINTS: readonly TaintMeta[] = [
  { key: "predicted", code: "p", label: "Built on a predicted input" },
  { key: "scenario_assumption", code: "a", label: "Built on a scenario assumption" },
  { key: "synthetic", code: "s", label: "Built on synthetic demonstration data" },
  { key: "user_provided", code: "u", label: "Built on a user-provided input" },
];
