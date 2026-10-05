import type { ProvenanceClass, Taint } from "../../api/client";
import { PROVENANCE, TAINTS, type BadgeShape } from "./provenance";

function Shape({ shape }: { shape: BadgeShape }) {
  const common = { fill: "currentColor", stroke: "currentColor", strokeWidth: 1.5 };
  let mark;
  switch (shape) {
    case "disc":
      mark = <circle cx="6" cy="6" r="4.5" {...common} />;
      break;
    case "ring":
      mark = <circle cx="6" cy="6" r="4" {...common} fill="none" />;
      break;
    case "square":
      mark = <rect x="1.75" y="1.75" width="8.5" height="8.5" {...common} />;
      break;
    case "diamond":
      mark = <polygon points="6,1 11,6 6,11 1,6" {...common} />;
      break;
    case "triangle":
      mark = <polygon points="6,1.25 11,10.5 1,10.5" {...common} />;
      break;
    case "dashed-ring":
      mark = <circle cx="6" cy="6" r="4" {...common} fill="none" strokeDasharray="2 1.5" />;
      break;
    case "hexagon":
      mark = <polygon points="3,1.5 9,1.5 11.5,6 9,10.5 3,10.5 0.5,6" {...common} fill="none" />;
      break;
    case "cross":
      mark = <path d="M2 2 L10 10 M10 2 L2 10" {...common} fill="none" strokeWidth={2.25} />;
      break;
  }
  return (
    <svg className="prov-shape" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
      {mark}
    </svg>
  );
}

export interface ProvenanceBadgeProps {
  provenance: ProvenanceClass;
}

/** Text code + shape + colour for a provenance class. Full description on hover and for AT. */
export function ProvenanceBadge({ provenance }: ProvenanceBadgeProps) {
  const meta = PROVENANCE[provenance];
  return (
    <span
      className="prov-badge"
      data-provenance={provenance}
      style={{ color: `var(${meta.colorVar})` }}
      title={`${meta.label}: ${meta.description}`}
      aria-label={`Provenance: ${meta.label}`}
      role="img"
    >
      <Shape shape={meta.shape} />
      <span className="prov-code" aria-hidden="true">
        {meta.code}
      </span>
    </span>
  );
}

/** Small markers for the kinds of input a value was built on. Renders nothing when clean. */
export function TaintFlags({ taint }: { taint: Taint }) {
  const active = TAINTS.filter((t) => taint[t.key]);
  if (active.length === 0) return null;
  return (
    <span className="taint-flags" aria-label={active.map((t) => t.label).join("; ")} role="img">
      {active.map((t) => (
        <span
          key={t.key}
          className="taint-flag"
          data-taint={t.key}
          title={t.label}
          aria-hidden="true"
        >
          {t.code}
        </span>
      ))}
    </span>
  );
}
