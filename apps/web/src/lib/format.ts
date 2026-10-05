/**
 * Number formatting for quantities. The browser only formats; it never recomputes a
 * scientific value (docs/frontend.md section 5).
 *
 * Significant figures follow the stated uncertainty: the uncertainty is shown to two
 * significant digits and the value is rounded to the same decimal position, as recommended
 * by the GUM (JCGM 100:2008, section 7.2.6). Without a stated uncertainty, values are shown
 * to DEFAULT_SIGNIFICANT_FIGURES, which is a display choice, not a claim about precision.
 */
import type { Uncertainty } from "../api/client";

export const LOCALE = "en";
export const DEFAULT_SIGNIFICANT_FIGURES = 4;
/** Digits kept in the uncertainty itself (GUM 7.2.6: "at most two"). */
export const UNCERTAINTY_DIGITS = 2;
const MAX_SIGNIFICANT_FIGURES = 15;
/** Upper limit Intl.NumberFormat accepts for fraction digits. */
const MAX_FRACTION_DIGITS = 20;
/** Magnitudes outside [SCI_LOW, SCI_HIGH) are shown in scientific notation. */
const SCI_LOW = 1e-3;
const SCI_HIGH = 1e6;

export const NOT_AVAILABLE = "not available";

/** A representative half-width of the uncertainty, used only to choose display precision. */
export function uncertaintyScale(u: Uncertainty | null): number | null {
  if (u === null) return null;
  switch (u.kind) {
    case "point":
      return null;
    case "uniform":
    case "triangular":
      return (u.max - u.min) / 2;
    case "interval":
      return (u.high - u.low) / 2;
    case "normal":
      return u.sd;
    case "lognormal":
      return (u.median * u.gsd - u.median / u.gsd) / 2;
    case "empirical":
      return (Math.max(...u.samples) - Math.min(...u.samples)) / 2;
  }
}

function exponent(x: number): number {
  return Math.floor(Math.log10(Math.abs(x)));
}

/** True if `scale` is a usable uncertainty half-width. */
function hasScale(scale: number | null): scale is number {
  return scale !== null && scale > 0 && Number.isFinite(scale);
}

/** Decimal exponent of the last digit kept, given an uncertainty half-width. */
function lastDigitExponent(scale: number): number {
  return exponent(scale) - (UNCERTAINTY_DIGITS - 1);
}

/** Significant figures for a non-zero `value` given an uncertainty half-width `scale`. */
export function significantFigures(value: number, scale: number | null): number {
  if (!hasScale(scale)) return DEFAULT_SIGNIFICANT_FIGURES;
  const sig = exponent(value) - lastDigitExponent(scale) + 1;
  return Math.min(MAX_SIGNIFICANT_FIGURES, Math.max(1, sig));
}

/** Format a number to exactly `sig` significant figures. */
export function formatNumber(value: number, sig: number): string {
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  const scientific = magnitude < SCI_LOW || magnitude >= SCI_HIGH;
  return new Intl.NumberFormat(LOCALE, {
    minimumSignificantDigits: sig,
    maximumSignificantDigits: sig,
    notation: scientific ? "scientific" : "standard",
  }).format(value);
}

/** A number shown at the resolution implied by an uncertainty half-width. */
function formatAtResolution(value: number, scale: number | null): string {
  if (value === 0 && hasScale(scale)) {
    // Zero has no significant figures; show it to the same decimal place instead.
    const decimals = Math.min(MAX_FRACTION_DIGITS, Math.max(0, -lastDigitExponent(scale)));
    return new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(0);
  }
  return formatNumber(value, significantFigures(value, scale));
}

/** The value as displayed, with precision set by its uncertainty. */
export function formatValue(value: number | null, u: Uncertainty | null): string {
  if (value === null) return NOT_AVAILABLE;
  return formatAtResolution(value, uncertaintyScale(u));
}

const formatBound = formatAtResolution;

/** Human-readable range or spread text for an uncertainty, or "" when there is none. */
export function formatUncertainty(u: Uncertainty | null): string {
  if (u === null) return "";
  const scale = uncertaintyScale(u);
  const sd = (x: number) => formatNumber(x, UNCERTAINTY_DIGITS);
  switch (u.kind) {
    case "point":
      return "";
    case "uniform":
      return `${formatBound(u.min, scale)} – ${formatBound(u.max, scale)} (uniform)`;
    case "triangular":
      return `${formatBound(u.min, scale)} – ${formatBound(u.max, scale)} (triangular, mode ${formatBound(u.mode, scale)})`;
    case "interval":
      return `${formatBound(u.low, scale)} – ${formatBound(u.high, scale)} (interval)`;
    case "normal":
      return `± ${sd(u.sd)} (1 sd)`;
    case "lognormal":
      return `×/÷ ${sd(u.gsd)} (geometric sd)`;
    case "empirical":
      return `${formatBound(Math.min(...u.samples), scale)} – ${formatBound(Math.max(...u.samples), scale)} (${u.samples.length} samples)`;
  }
}
