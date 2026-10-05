import { describe, expect, it } from "vitest";

import {
  DEFAULT_SIGNIFICANT_FIGURES,
  formatNumber,
  formatUncertainty,
  formatValue,
  NOT_AVAILABLE,
  significantFigures,
  uncertaintyScale,
} from "./format";

// Expected strings are worked by hand from the GUM rule: uncertainty to two significant
// digits, value rounded to the same decimal position.
describe("significantFigures", () => {
  it("uses the default without an uncertainty", () => {
    expect(significantFigures(12.3456, null)).toBe(DEFAULT_SIGNIFICANT_FIGURES);
  });

  it("follows the uncertainty", () => {
    // half-width 2.45 -> shown as 2.5, last digit at 1e-1; 12.3456 -> 12.3 (3 s.f.)
    expect(significantFigures(12.3456, 2.45)).toBe(3);
    // sd 0.000021 -> last digit at 1e-6; 0.0012346 -> 0.001235 (4 s.f.)
    expect(significantFigures(0.0012346, 0.000021)).toBe(4);
    // uncertainty larger than the value still keeps one figure
    expect(significantFigures(3, 4000)).toBe(1);
  });
});

describe("formatValue", () => {
  it("never shows a missing value as zero", () => {
    expect(formatValue(null, null)).toBe(NOT_AVAILABLE);
  });

  it("formats with uncertainty-driven precision", () => {
    const tri = { kind: "triangular", min: 10.1, mode: 12.4, max: 15.0 } as const;
    expect(formatValue(12.3456, tri)).toBe("12.3");
    expect(formatValue(0.0012346, { kind: "normal", mean: 0.0012346, sd: 0.000021 })).toBe(
      "0.001235",
    );
  });

  it("keeps significant trailing zeros", () => {
    expect(formatNumber(2.5, 3)).toBe("2.50");
  });

  it("uses grouping and scientific notation at the extremes", () => {
    expect(formatValue(1234.5678, null)).toBe("1,235");
    expect(formatValue(1234567, null)).toBe("1.235E6");
    expect(formatValue(0.00001234, null)).toBe("1.234E-5");
    expect(formatValue(0, null)).toBe("0");
  });

  it("shows zero at the resolution of its uncertainty", () => {
    // half-width 0.05 -> last digit at 1e-3
    expect(formatValue(0, { kind: "uniform", min: -0.05, max: 0.05 })).toBe("0.000");
  });
});

describe("uncertaintyScale", () => {
  it("computes a half-width for each kind", () => {
    expect(uncertaintyScale({ kind: "point" })).toBeNull();
    expect(uncertaintyScale({ kind: "uniform", min: 1, max: 3 })).toBe(1);
    expect(uncertaintyScale({ kind: "interval", low: 0, high: 10 })).toBe(5);
    expect(uncertaintyScale({ kind: "normal", mean: 0, sd: 0.2 })).toBe(0.2);
    // (2 * 2 - 2 / 2) / 2 = 1.5
    expect(uncertaintyScale({ kind: "lognormal", median: 2, gsd: 2 })).toBe(1.5);
    expect(uncertaintyScale({ kind: "empirical", samples: [4, 1, 9] })).toBe(4);
  });
});

describe("formatUncertainty", () => {
  it("describes each kind", () => {
    expect(formatUncertainty(null)).toBe("");
    expect(formatUncertainty({ kind: "point" })).toBe("");
    expect(formatUncertainty({ kind: "triangular", min: 10.1, mode: 12.4, max: 15.0 })).toBe(
      "10.1 – 15.0 (triangular, mode 12.4)",
    );
    expect(formatUncertainty({ kind: "uniform", min: 1, max: 3 })).toBe("1.0 – 3.0 (uniform)");
    expect(formatUncertainty({ kind: "interval", low: 0, high: 10 })).toBe("0.0 – 10.0 (interval)");
    expect(formatUncertainty({ kind: "normal", mean: 5, sd: 0.123 })).toBe("± 0.12 (1 sd)");
    expect(formatUncertainty({ kind: "lognormal", median: 2, gsd: 1.5 })).toBe(
      "×/÷ 1.5 (geometric sd)",
    );
    expect(formatUncertainty({ kind: "empirical", samples: [4, 1, 9] })).toBe(
      "1.0 – 9.0 (3 samples)",
    );
  });
});
