/** Parse Indian-formatted amount string to number (lakhs grouping). */
export function parseIndianAmount(input: string): number | null {
  const trimmed = input.replace(/[₹\s]/g, "").trim();
  if (!trimmed) return null;
  const normalized = trimmed.replace(/,/g, "");
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) return null;
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

/** Format number as INR with Indian digit grouping (₹1,23,456.78). */
export function formatIndianAmount(value: number | string): string {
  const n =
    typeof value === "string" ? parseIndianAmount(value) : value;
  if (n === null || !Number.isFinite(n)) return String(value);
  const [intPart, fracPart = ""] = n.toFixed(2).split(".");
  const sign = intPart.startsWith("-") ? "-" : "";
  const digits = intPart.replace("-", "");
  const lastThree = digits.slice(-3);
  const rest = digits.slice(0, -3);
  const groupedRest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  const intFormatted =
    rest.length > 0 ? `${groupedRest},${lastThree}` : lastThree;
  return `₹${sign}${intFormatted}.${fracPart}`;
}
