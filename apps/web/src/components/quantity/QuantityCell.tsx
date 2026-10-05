import type { QuantityOut } from "../../api/client";
import { formatUncertainty, formatValue } from "../../lib/format";
import { ProvenanceBadge, TaintFlags } from "../provenance/ProvenanceBadge";

export interface QuantityCellProps {
  quantity: QuantityOut;
  /** Opens the trace panel for a stored result (docs/frontend.md section 2, contract 5). */
  onOpenTrace?: (resultId: string) => void;
}

/**
 * The only way a number is shown: value at uncertainty-driven precision, unit, range text,
 * provenance badge and taint markers. A bare number without unit and provenance is a bug.
 */
export function QuantityCell({ quantity, onOpenTrace }: QuantityCellProps) {
  const { value, unit, uncertainty, provenance, taint, result_id: resultId } = quantity;
  const available = value !== null;
  const range = formatUncertainty(uncertainty);
  return (
    <span
      className="quantity-cell"
      data-available={available}
      data-synthetic={taint.synthetic || provenance === "SYNTHETIC_DEMO"}
    >
      <span className="quantity-value">{formatValue(value, uncertainty)}</span>
      {available && <span className="quantity-unit">{unit}</span>}
      {range && <span className="quantity-range">{range}</span>}
      <ProvenanceBadge provenance={provenance} />
      <TaintFlags taint={taint} />
      {resultId !== null && onOpenTrace && (
        <button
          type="button"
          className="quantity-trace"
          onClick={() => {
            onOpenTrace(resultId);
          }}
        >
          Trace
        </button>
      )}
    </span>
  );
}
