const GST_STATE_CODES = new Set(
  [...Array.from({ length: 38 }, (_, i) => String(i + 1).padStart(2, "0")), "97", "99"],
);

const CHECKSUM_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function gstinChecksumChar(first14: string): string {
  const upper = first14.toUpperCase();
  let total = 0;
  for (let i = 0; i < upper.length; i++) {
    const ch = upper[i];
    const val = CHECKSUM_CHARS.indexOf(ch);
    if (val < 0) throw new Error("invalid char");
    const factor = (i % 2) + 1;
    if (factor === 1) {
      total += val;
    } else {
      const doubled = val * 2;
      total += Math.floor(doubled / 36) + (doubled % 36);
    }
  }
  const rem = total % 36;
  const check = (36 - rem) % 36;
  return CHECKSUM_CHARS[check];
}

export function isValidGstin(s: string): boolean {
  if (!s || s.length !== 15) return false;
  const upper = s.toUpperCase();
  if (!/^[0-9A-Z]{15}$/.test(upper)) return false;
  if (!GST_STATE_CODES.has(upper.slice(0, 2))) return false;
  try {
    return upper[14] === gstinChecksumChar(upper.slice(0, 14));
  } catch {
    return false;
  }
}
