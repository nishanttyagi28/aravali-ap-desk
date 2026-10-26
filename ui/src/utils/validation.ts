import { isValidGstin } from "./gstin";
import { parseIndianAmount } from "./currency";

export interface CorrectionValues {
  vendor_gstin?: string;
  buyer_gstin?: string;
  grand_total?: string;
  taxable_total?: string;
  cgst_total?: string;
  sgst_total?: string;
  igst_total?: string;
}

export interface FieldError {
  field: string;
  message: string;
}

export function validateCorrections(values: CorrectionValues): FieldError[] {
  const errors: FieldError[] = [];

  if (values.vendor_gstin !== undefined && values.vendor_gstin !== "") {
    if (!isValidGstin(values.vendor_gstin)) {
      errors.push({
        field: "vendor_gstin",
        message: "Invalid vendor GSTIN (15 characters, valid checksum)",
      });
    }
  }
  if (values.buyer_gstin !== undefined && values.buyer_gstin !== "") {
    if (!isValidGstin(values.buyer_gstin)) {
      errors.push({
        field: "buyer_gstin",
        message: "Invalid buyer GSTIN (15 characters, valid checksum)",
      });
    }
  }

  const amountFields: (keyof CorrectionValues)[] = [
    "grand_total",
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
  ];
  for (const field of amountFields) {
    const raw = values[field];
    if (raw === undefined || raw === "") continue;
    const parsed = parseIndianAmount(raw);
    if (parsed === null || parsed < 0) {
      errors.push({
        field,
        message: "Enter a valid non-negative amount (e.g. ₹1,23,456.78)",
      });
    }
  }

  return errors;
}

export function canPostToLedger(outcome: string, posted: boolean): boolean {
  return outcome === "ALLOW" && !posted;
}
