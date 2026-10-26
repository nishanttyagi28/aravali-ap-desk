import { describe, expect, it } from "vitest";
import { canPostToLedger, validateCorrections } from "./validation";

describe("validateCorrections", () => {
  it("rejects invalid GSTIN", () => {
    const errors = validateCorrections({ vendor_gstin: "INVALIDGSTIN00" });
    expect(errors.some((e) => e.field === "vendor_gstin")).toBe(true);
  });

  it("accepts valid GSTIN from fixtures", () => {
    const errors = validateCorrections({ vendor_gstin: "27YTCVR4268P1ZW" });
    expect(errors).toHaveLength(0);
  });

  it("rejects bad amounts", () => {
    const errors = validateCorrections({ grand_total: "not-a-number" });
    expect(errors.some((e) => e.field === "grand_total")).toBe(true);
  });
});

describe("canPostToLedger", () => {
  it("allows ALLOW when not posted", () => {
    expect(canPostToLedger("ALLOW", false)).toBe(true);
  });

  it("blocks REVIEW and BLOCK", () => {
    expect(canPostToLedger("REVIEW", false)).toBe(false);
    expect(canPostToLedger("BLOCK", false)).toBe(false);
  });

  it("blocks when already posted", () => {
    expect(canPostToLedger("ALLOW", true)).toBe(false);
  });
});
