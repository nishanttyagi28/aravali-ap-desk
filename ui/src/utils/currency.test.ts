import { describe, expect, it } from "vitest";
import { formatIndianAmount, parseIndianAmount } from "./currency";

describe("Indian amount formatting", () => {
  it("formats lakhs grouping", () => {
    expect(formatIndianAmount(123456.78)).toBe("₹1,23,456.78");
  });

  it("parses formatted input", () => {
    expect(parseIndianAmount("₹1,23,456.78")).toBe(123456.78);
  });
});
