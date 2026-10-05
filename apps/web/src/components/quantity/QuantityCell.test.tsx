import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { QuantityOut } from "../../api/client";
import { QuantityCell } from "./QuantityCell";

const CLEAN = {
  predicted: false,
  scenario_assumption: false,
  synthetic: false,
  user_provided: false,
};

function quantity(overrides: Partial<QuantityOut> = {}): QuantityOut {
  return {
    value: 12.3456,
    unit: "t/yr",
    uncertainty: { kind: "triangular", min: 10.1, mode: 12.4, max: 15.0 },
    provenance: "DERIVED",
    taint: CLEAN,
    source_ref: null,
    result_id: null,
    ...overrides,
  };
}

describe("QuantityCell", () => {
  it("shows value, unit, range and provenance together", () => {
    const { container } = render(<QuantityCell quantity={quantity()} />);
    expect(container.querySelector(".quantity-value")).toHaveTextContent("12.3");
    expect(container.querySelector(".quantity-unit")).toHaveTextContent("t/yr");
    expect(container.querySelector(".quantity-range")).toHaveTextContent(
      "10.1 – 15.0 (triangular, mode 12.4)",
    );
    expect(screen.getByRole("img", { name: "Provenance: Derived" })).toHaveTextContent("DER");
  });

  it("shows a missing value as not available, never as zero", () => {
    const { container } = render(
      <QuantityCell quantity={quantity({ value: null, uncertainty: null })} />,
    );
    expect(container.querySelector(".quantity-value")).toHaveTextContent("not available");
    expect(container.querySelector(".quantity-unit")).toBeNull();
    expect(container.textContent).not.toContain("0");
  });

  it("marks taints and synthetic data", () => {
    const { container } = render(
      <QuantityCell
        quantity={quantity({ taint: { ...CLEAN, synthetic: true, predicted: true } })}
      />,
    );
    expect(container.querySelector(".quantity-cell")).toHaveAttribute("data-synthetic", "true");
    expect(
      screen.getByRole("img", {
        name: "Built on a predicted input; Built on synthetic demonstration data",
      }),
    ).toBeInTheDocument();
  });

  it("opens the trace for stored results", async () => {
    const onOpenTrace = vi.fn();
    render(<QuantityCell quantity={quantity({ result_id: "r-1" })} onOpenTrace={onOpenTrace} />);
    await userEvent.click(screen.getByRole("button", { name: "Trace" }));
    expect(onOpenTrace).toHaveBeenCalledWith("r-1");
  });

  it("offers no trace button without a stored result", () => {
    render(<QuantityCell quantity={quantity()} onOpenTrace={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Trace" })).toBeNull();
  });
});
