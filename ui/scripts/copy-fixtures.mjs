import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const uiRoot = resolve(__dirname, "..");
const sampleDir = resolve(uiRoot, "..", "datasets", "sample");
const fixturesDir = resolve(uiRoot, "public", "fixtures");

if (!existsSync(sampleDir)) {
  console.warn("copy-fixtures: datasets/sample not found, skipping");
  process.exit(0);
}

mkdirSync(fixturesDir, { recursive: true });

const pdfs = readdirSync(sampleDir).filter((f) => f.endsWith(".pdf"));
for (const pdf of pdfs) {
  copyFileSync(join(sampleDir, pdf), join(fixturesDir, pdf));
}

console.log(`copy-fixtures: copied ${pdfs.length} PDF(s) to public/fixtures/`);

import("./build-mock-data.mjs");
