import type { components } from "../api/schema";
import type { ExtractedInvoice } from "../api/types";

type ExtractedField = components["schemas"]["ExtractedField"];

export interface FieldEntry {
  name: string;
  field: ExtractedField;
}

export function listExtractedFields(invoice: ExtractedInvoice): FieldEntry[] {
  const fields = invoice.fields ?? {};
  return Object.keys(fields)
    .sort()
    .map((name) => ({ name, field: fields[name] }))
    .filter((e) => e.field.bbox != null);
}
