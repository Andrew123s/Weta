import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ProvenanceClass } from "../../api/client";
import openapi from "../../api/openapi.json";
import { ProvenanceBadge, TaintFlags } from "./ProvenanceBadge";
import { PROVENANCE } from "./provenance";

const API_CLASSES = openapi.components.schemas.ProvenanceClass.enum as ProvenanceClass[];

describe("ProvenanceBadge", () => {
  it("covers exactly the provenance classes the API defines", () => {
    expect(Object.keys(PROVENANCE).sort()).toEqual([...API_CLASSES].sort());
  });

  it("gives every class a distinct code and a distinct shape", () => {
    const metas = Object.values(PROVENANCE);
    expect(new Set(metas.map((m) => m.code)).size).toBe(metas.length);
    expect(new Set(metas.map((m) => m.shape)).size).toBe(metas.length);
  });

  it.each(API_CLASSES)("renders text, shape and accessible label for %s", (cls) => {
    const { container } = render(<ProvenanceBadge provenance={cls} />);
    const meta = PROVENANCE[cls];
    const badge = screen.getByRole("img", { name: `Provenance: ${meta.label}` });
    expect(badge).toHaveTextContent(meta.code);
    expect(badge).toHaveAttribute("title", `${meta.label}: ${meta.description}`);
    expect(container.querySelector("svg.prov-shape")).not.toBeNull();
  });
});

describe("TaintFlags", () => {
  it("renders nothing for a clean value", () => {
    const clean = {
      predicted: false,
      scenario_assumption: false,
      synthetic: false,
      user_provided: false,
    };
    const { container } = render(<TaintFlags taint={clean} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows one marker per taint", () => {
    const { container } = render(
      <TaintFlags
        taint={{
          predicted: false,
          scenario_assumption: true,
          synthetic: false,
          user_provided: true,
        }}
      />,
    );
    const flags = [...container.querySelectorAll(".taint-flag")].map((el) => el.textContent);
    expect(flags).toEqual(["a", "u"]);
  });
});
