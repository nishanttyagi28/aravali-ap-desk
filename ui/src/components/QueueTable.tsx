import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { DecisionOutcome, ReviewQueueItem } from "../api/client";
import { DecisionBadge } from "./DecisionBadge";
import { formatIndianAmount } from "../utils/currency";
import styles from "./QueueTable.module.css";

const ISSUE_CODES = [
  "GSTIN_CHECKSUM",
  "GSTIN_STATE_MISMATCH",
  "TAX_REGIME_MISMATCH",
  "LINE_ARITHMETIC",
  "TOTAL_MISMATCH",
  "DUPLICATE_INVOICE",
  "VENDOR_UNKNOWN",
  "LOW_CONFIDENCE",
  "MISSING_FIELD",
  "ROUND_OFF_EXCEEDED",
] as const;

export interface QueueFilters {
  decision: DecisionOutcome[];
  issue_code: string[];
}

interface Props {
  items: ReviewQueueItem[];
  filters: QueueFilters;
  onFiltersChange: (f: QueueFilters) => void;
  loading?: boolean;
}

export function QueueTable({ items, filters, onFiltersChange, loading }: Props) {
  const [focusIndex, setFocusIndex] = useState(0);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  const toggleDecision = (d: DecisionOutcome) => {
    const set = new Set(filters.decision);
    if (set.has(d)) set.delete(d);
    else set.add(d);
    onFiltersChange({ ...filters, decision: [...set] });
  };

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!items.length) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusIndex((i) => Math.min(i + 1, items.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        const item = items[focusIndex];
        if (item) {
          window.location.href = `/invoices/${item.invoice_id}`;
        }
      }
    },
    [items, focusIndex],
  );

  useEffect(() => {
    rowRefs.current[focusIndex]?.focus();
  }, [focusIndex, items]);

  return (
    <div className={styles.wrap} onKeyDown={onKeyDown}>
      <div className={styles.filters} role="group" aria-label="Queue filters">
        <span className={styles.filterLabel}>Decision</span>
        {(["ALLOW", "REVIEW", "BLOCK"] as DecisionOutcome[]).map((d) => (
          <label key={d} className={styles.chip}>
            <input
              type="checkbox"
              checked={filters.decision.includes(d)}
              onChange={() => toggleDecision(d)}
            />
            {d}
          </label>
        ))}
        <span className={styles.filterLabel}>Issue</span>
        <select
          className={styles.issueSelect}
          aria-label="Filter by issue code"
          value={filters.issue_code[0] ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            onFiltersChange({
              ...filters,
              issue_code: v ? [v] : [],
            });
          }}
        >
          <option value="">All issues</option>
          {ISSUE_CODES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Vendor</th>
            <th scope="col">Invoice #</th>
            <th scope="col">Date</th>
            <th scope="col">Grand total</th>
            <th scope="col">Decision</th>
            <th scope="col">Top issue</th>
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td colSpan={6}>Loading…</td>
            </tr>
          )}
          {!loading && items.length === 0 && (
            <tr>
              <td colSpan={6}>No invoices match filters.</td>
            </tr>
          )}
          {items.map((item, idx) => (
            <tr
              key={item.invoice_id}
              ref={(el) => {
                rowRefs.current[idx] = el;
              }}
              tabIndex={idx === focusIndex ? 0 : -1}
              className={idx === focusIndex ? styles.focused : undefined}
              onFocus={() => setFocusIndex(idx)}
            >
              <td>{item.vendor_name ?? item.vendor_gstin ?? "—"}</td>
              <td>
                <Link to={`/invoices/${item.invoice_id}`}>
                  {item.invoice_number ?? item.invoice_id.slice(0, 8)}
                </Link>
              </td>
              <td>{item.invoice_date ?? "—"}</td>
              <td>{formatIndianAmount(item.grand_total)}</td>
              <td>
                <DecisionBadge outcome={item.outcome} />
              </td>
              <td>{item.top_issue_code ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className={styles.hint}>↑↓ navigate rows, Enter open invoice</p>
    </div>
  );
}

export { ISSUE_CODES };
