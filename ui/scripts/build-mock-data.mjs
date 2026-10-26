import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const uiRoot = resolve(__dirname, "..");
const sampleDir = resolve(uiRoot, "..", "datasets", "sample");
const outPath = resolve(uiRoot, "src", "mock", "data.json");

const vendorMaster = JSON.parse(
  readFileSync(join(sampleDir, "vendor_master.json"), "utf8"),
);
const vendorByGstin = new Map(
  vendorMaster.vendors.map((v) => [v.gstin.toUpperCase(), v]),
);

const truths = readdirSync(sampleDir)
  .filter((f) => f.endsWith(".truth.json"))
  .map((f) => {
    const raw = JSON.parse(readFileSync(join(sampleDir, f), "utf8"));
    const inv = raw.invoice;
    const gstin = (inv.vendor_gstin || "").toUpperCase();
    const vendor = vendorByGstin.get(gstin);
    return {
      invoice_id: inv.invoice_id,
      expected_decision: raw.expected_decision,
      expected_issue_codes: raw.expected_issue_codes ?? [],
      invoice: inv,
      vendor_name: vendor?.legal_name ?? null,
      vendor_id: vendor?.vendor_id ?? "UNKNOWN",
    };
  });

writeFileSync(outPath, JSON.stringify({ invoices: truths }, null, 0), "utf8");
console.log(`build-mock-data: wrote ${truths.length} invoices to src/mock/data.json`);
