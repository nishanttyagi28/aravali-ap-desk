import { useMemo, useState } from "react";
import type { ExtractedInvoice } from "../api/types";
import { formatIndianAmount } from "../utils/currency";
import {
  validateCorrections,
  type CorrectionValues,
} from "../utils/validation";
import styles from "./CorrectionForm.module.css";

const EDITABLE: { key: keyof CorrectionValues; label: string }[] = [
  { key: "vendor_gstin", label: "Vendor GSTIN" },
  { key: "buyer_gstin", label: "Buyer GSTIN" },
  { key: "taxable_total", label: "Taxable total" },
  { key: "cgst_total", label: "CGST total" },
  { key: "sgst_total", label: "SGST total" },
  { key: "igst_total", label: "IGST total" },
  { key: "grand_total", label: "Grand total" },
];

interface Props {
  invoice: ExtractedInvoice;
  highlighted: string | null;
  onHighlight: (name: string | null) => void;
  onSubmitCorrections: (corrections: Record<string, string>) => void;
  disabled?: boolean;
}

export function CorrectionForm({
  invoice,
  highlighted,
  onHighlight,
  onSubmitCorrections,
  disabled,
}: Props) {
  const initial = useMemo(() => {
    const v: CorrectionValues = {};
    for (const { key } of EDITABLE) {
      const val = invoice[key as keyof ExtractedInvoice];
      if (typeof val === "string") v[key] = val;
    }
    return v;
  }, [invoice]);

  const [values, setValues] = useState<CorrectionValues>(initial);
  const errors = validateCorrections(values);

  const onChange = (key: keyof CorrectionValues, raw: string) => {
    setValues((prev) => ({ ...prev, [key]: raw }));
  };

  const formatOnBlur = (key: keyof CorrectionValues) => {
    const raw = values[key];
    if (!raw || key.includes("gstin")) return;
    const n = formatIndianAmount(raw);
    if (n.startsWith("₹")) setValues((prev) => ({ ...prev, [key]: n }));
  };

  return (
    <section className={styles.panel} aria-labelledby="fields-heading">
      <h2 id="fields-heading">Extracted fields</h2>
      <form
        id="corrections-form"
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault();
          if (errors.length) return;
          const corrections: Record<string, string> = {};
          for (const { key } of EDITABLE) {
            const next = values[key];
            const orig = initial[key];
            if (next !== undefined && next !== orig) {
              corrections[key] = key.includes("total")
                ? next.replace(/[₹,\s]/g, "")
                : next;
            }
          }
          onSubmitCorrections(corrections);
        }}
      >
        <ul className={styles.fieldList}>
          {EDITABLE.map(({ key, label }) => {
            const fieldMeta = invoice.fields?.[key];
            const err = errors.find((e) => e.field === key);
            const active = highlighted === key;
            return (
              <li
                key={key}
                className={active ? styles.active : undefined}
                onMouseEnter={() => onHighlight(key)}
                onMouseLeave={() => onHighlight(null)}
              >
                <label htmlFor={`field-${key}`}>
                  {label}
                  {fieldMeta && (
                    <span className={styles.conf}>
                      {(fieldMeta.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </label>
                <input
                  id={`field-${key}`}
                  name={key}
                  value={values[key] ?? ""}
                  disabled={disabled}
                  onChange={(e) => onChange(key, e.target.value)}
                  onBlur={() => formatOnBlur(key)}
                  aria-invalid={Boolean(err)}
                  aria-describedby={err ? `err-${key}` : undefined}
                />
                {err && (
                  <span id={`err-${key}`} className={styles.fieldError} role="alert">
                    {err.message}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </form>
    </section>
  );
}
