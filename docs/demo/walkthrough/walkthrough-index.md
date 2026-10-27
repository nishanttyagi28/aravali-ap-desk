# Aravali AP Desk - VS Code code walkthrough index

Silent VS Code screen recording (1600x856, taskbar cropped): Explorer + editor open every source/config file of the repo in project-tour order, for voice-over. `Time` is mm:ss inside each part; `Cum.` is the running time across parts 1-5 played back to back.

Total: 240 files across 5 parts, 0:41:58 combined. Shown in the Explorer only (not opened): `ui/package-lock.json`, the sample/fixture PDFs, `bi/data/receipts/2..32.json`, `bi/data/mis.xlsx`, 8 of 9 `datasets/sample/*.truth.json`, `docs/demo/aravali-demo.mp4`, `.gitkeep` files; untracked `.venv/`, `node_modules/`, `data/`, `ui/dist/`.

## Part 1 - Overview & top-level config

`part1-overview-config.mp4` - 08:37 (518 s), 8.5 MB, 38 files.

| Time | Cum. | File | Purpose |
|---|---|---|---|
| 00:07 | 0:00:07 | `README.md` | Aravali AP Desk |
| 00:28 | 0:00:28 | `SETUP.md` | Run Aravali AP Desk on a new machine |
| 00:45 | 0:00:45 | `AGENTS.md` | Aravali AP Desk — multi-agent rules (M1) |
| 01:00 | 0:01:00 | `CHANGELOG.md` | Changelog |
| 01:14 | 0:01:14 | `LICENSE` | MIT licence. |
| 01:27 | 0:01:27 | `pyproject.toml` | Python package metadata, dependencies/extras, ruff + pytest config. |
| 01:42 | 0:01:42 | `requirements-lock.txt` | Pinned Python dependency versions from the verified Windows venv. |
| 01:59 | 0:01:59 | `Makefile` | Linux/macOS shortcuts: install, dev, test, eval. |
| 02:13 | 0:02:13 | `.env.example` | Template env vars: GROQ_API_KEY (optional LLM mode), EXTRACT_MODE=offline. |
| 02:26 | 0:02:26 | `.gitattributes` | Line-ending rules (LF) for the repo. |
| 02:39 | 0:02:39 | `.gitignore` | Files git ignores (venv, node_modules, local data, generated datasets). |
| 02:52 | 0:02:52 | `.github/workflows/ci.yml` | GitHub Actions CI: ruff, pytest, eval gate, UI lint/typecheck/tests. |
| 03:14 | 0:03:14 | `.cursor/hooks.json` | Cursor agent hooks: run scope_guard before every edit/shell command (fail-closed). |
| 03:21 | 0:03:21 | `.cursor/hooks/ownership.json` | Per-role path allowlists and frozen files for the agents. |
| 03:30 | 0:03:30 | `.cursor/hooks/scope_guard.py` | Cursor hook: enforce agent role path and shell allowlists (stdlib only). |
| 03:51 | 0:03:51 | `.vscode/tasks.json` | VS Code tasks that drive the supervisor harness (run agent, gate, approve & push). |
| 04:12 | 0:04:12 | `scripts/dev.ps1` | Start API + UI against the real offline stack (Windows). |
| 04:19 | 0:04:19 | `scripts/export_schemas.py` | Export Pydantic contract models to JSON Schema files under schemas/. |
| 04:37 | 0:04:37 | `openapi.yaml` | OpenAPI contract for the FastAPI backend. |
| 04:58 | 0:04:58 | `schemas/index.json` | JSON Schema for index |
| 05:05 | 0:05:05 | `schemas/BBox.schema.json` | Axis-aligned rectangle on a PDF page. |
| 05:14 | 0:05:14 | `schemas/Decision.schema.json` | JSON Schema for Decision |
| 05:29 | 0:05:29 | `schemas/ErrorResponse.schema.json` | JSON Schema for ErrorResponse |
| 05:38 | 0:05:38 | `schemas/ExtractedField.schema.json` | One extracted scalar with provenance. |
| 05:51 | 0:05:51 | `schemas/ExtractedInvoice.schema.json` | JSON Schema for ExtractedInvoice |
| 06:07 | 0:06:07 | `schemas/InvoiceHistory.schema.json` | Ordered duplicate-detection index (manifest build order). |
| 06:16 | 0:06:16 | `schemas/InvoiceHistoryRecord.schema.json` | JSON Schema for InvoiceHistoryRecord |
| 06:31 | 0:06:31 | `schemas/LedgerEntry.schema.json` | JSON Schema for LedgerEntry |
| 06:44 | 0:06:44 | `schemas/LineItem.schema.json` | JSON Schema for LineItem |
| 06:55 | 0:06:55 | `schemas/Metrics.schema.json` | JSON Schema for Metrics |
| 07:04 | 0:07:04 | `schemas/ReviewAction.schema.json` | JSON Schema for ReviewAction |
| 07:13 | 0:07:13 | `schemas/ReviewQueueItem.schema.json` | JSON Schema for ReviewQueueItem |
| 07:29 | 0:07:29 | `schemas/ReviewResult.schema.json` | JSON Schema for ReviewResult |
| 07:44 | 0:07:44 | `schemas/SealRef.schema.json` | JSON Schema for SealRef |
| 07:53 | 0:07:53 | `schemas/TruthRecord.schema.json` | JSON Schema for TruthRecord |
| 08:08 | 0:08:08 | `schemas/ValidationIssue.schema.json` | JSON Schema for ValidationIssue |
| 08:19 | 0:08:19 | `schemas/Vendor.schema.json` | JSON Schema for Vendor |
| 08:28 | 0:08:28 | `schemas/VendorMaster.schema.json` | JSON Schema for VendorMaster |

## Part 2 - Document AI: contracts, ingest, extract, validate

`part2-docai.mp4` - 05:31 (331 s), 5.8 MB, 36 files.

| Time | Cum. | File | Purpose |
|---|---|---|---|
| 00:07 | 0:08:45 | `docai/__init__.py` | Aravali AP Desk — document AI core. |
| 00:14 | 0:08:52 | `docai/contracts/__init__.py` | Pydantic v2 contracts (frozen after M1). |
| 00:23 | 0:09:01 | `docai/contracts/bbox.py` | Bounding boxes in PDF user space. |
| 00:30 | 0:09:08 | `docai/contracts/decision.py` | Decision contract. |
| 00:37 | 0:09:15 | `docai/contracts/errors.py` | API error envelope. |
| 00:44 | 0:09:22 | `docai/contracts/extracted.py` | Extraction contracts. |
| 00:56 | 0:09:33 | `docai/contracts/gstin.py` | GSTIN checksum and state-code helpers (pure, no I/O). |
| 01:05 | 0:09:42 | `docai/contracts/ledger.py` | Ledger posting contracts. |
| 01:14 | 0:09:51 | `docai/contracts/metrics.py` | API metrics snapshot. |
| 01:21 | 0:09:59 | `docai/contracts/review.py` | Human review contracts. |
| 01:30 | 0:10:08 | `docai/contracts/truth.py` | Synthetic / eval ground-truth record. |
| 01:37 | 0:10:15 | `docai/contracts/validation.py` | Validation issue contracts. |
| 01:44 | 0:10:22 | `docai/contracts/vendor.py` | Vendor master and invoice history. |
| 01:53 | 0:10:31 | `docai/ingest/__init__.py` | PDF ingest (M2 — agent A). |
| 02:00 | 0:10:38 | `docai/ingest/errors.py` | Ingest errors. |
| 02:07 | 0:10:45 | `docai/ingest/models.py` | Ingest document models. |
| 02:15 | 0:10:52 | `docai/ingest/pdf.py` | PDF loading via pdfplumber with optional OCR. |
| 02:28 | 0:11:05 | `docai/ingest/ocr.py` | OCR backends for scanned pages. |
| 02:41 | 0:11:18 | `docai/extract/__init__.py` | Invoice extraction (M2 — agent A). |
| 02:50 | 0:11:28 | `docai/extract/version.py` |  |
| 02:57 | 0:11:35 | `docai/extract/offline.py` | Rule-based offline invoice extraction. |
| 03:12 | 0:11:50 | `docai/extract/llm.py` | Optional LLM fallback for low-confidence fields. |
| 03:23 | 0:12:01 | `docai/validate/__init__.py` | GST validation engine (M2 — agent B). |
| 03:34 | 0:12:12 | `docai/validate/policy.py` | Decision policy: map validation issue codes to ALLOW / REVIEW / BLOCK. |
| 03:43 | 0:12:21 | `docai/validate/util.py` | Shared validation helpers. |
| 03:53 | 0:12:30 | `docai/validate/rules/__init__.py` | One module per validation rule. |
| 04:00 | 0:12:37 | `docai/validate/rules/duplicate.py` | Defines check_duplicate. |
| 04:09 | 0:12:47 | `docai/validate/rules/gst_rate.py` | Defines check_gst_rates. |
| 04:16 | 0:12:54 | `docai/validate/rules/gstin.py` | Defines check_gstin_checksum, check_gstin_state. |
| 04:25 | 0:13:03 | `docai/validate/rules/lines.py` | Defines check_line_arithmetic. |
| 04:36 | 0:13:14 | `docai/validate/rules/low_confidence.py` | Defines check_low_confidence. |
| 04:43 | 0:13:21 | `docai/validate/rules/missing.py` | Defines check_missing_fields. |
| 04:52 | 0:13:30 | `docai/validate/rules/round_off.py` | Defines check_round_off. |
| 04:59 | 0:13:37 | `docai/validate/rules/tax_regime.py` | Defines _regime_from_pos, _regime_from_lines, check_tax_regime. |
| 05:13 | 0:13:50 | `docai/validate/rules/totals.py` | Defines check_totals. |
| 05:24 | 0:14:01 | `docai/validate/rules/vendor.py` | Defines check_vendor, _extract_vendor_name. |

## Part 3 - Ledger, DB, API

`part3-ledger-api.mp4` - 03:09 (189 s), 3.4 MB, 16 files.

| Time | Cum. | File | Purpose |
|---|---|---|---|
| 00:07 | 0:14:16 | `ledger/__init__.py` | Append-only ledger posting. |
| 00:14 | 0:14:23 | `ledger/posting.py` | Ledger posting with hash-chained KarmaSakshi-style stub receipts. |
| 00:29 | 0:14:38 | `ledger/receipt.py` | KarmaSakshi-style effect receipt canonicalisation and hashing. |
| 00:40 | 0:14:49 | `ledger/seal.py` | Seal providers for tamper-evident ledger manifests. |
| 00:49 | 0:14:58 | `ledger/verify.py` | CLI: python -m ledger.verify [--db <url or path>] |
| 01:04 | 0:15:13 | `db/__init__.py` | Persistence layer. |
| 01:11 | 0:15:20 | `db/models.py` | SQLAlchemy 2.0 models. |
| 01:25 | 0:15:34 | `db/session.py` | Database engine and session factory. |
| 01:40 | 0:15:49 | `db/repository.py` | High-level persistence helpers for API and ledger. |
| 02:01 | 0:16:10 | `api/__init__.py` | HTTP API for Aravali AP Desk. |
| 02:08 | 0:16:17 | `api/__main__.py` |  |
| 02:15 | 0:16:24 | `api/serve.py` | CLI entry: ``python -m api.serve``. |
| 02:22 | 0:16:31 | `api/deps.py` | FastAPI dependencies and app state. |
| 02:31 | 0:16:40 | `api/services.py` | Business logic for HTTP handlers. |
| 02:46 | 0:16:55 | `api/seed.py` | Idempotent local DB seed: vendor master + sample invoices. |
| 02:56 | 0:17:04 | `api/main.py` | FastAPI application matching openapi.yaml. |

## Part 4 - Review UI (ui/)

`part4-ui.mp4` - 09:35 (576 s), 10.8 MB, 61 files.

| Time | Cum. | File | Purpose |
|---|---|---|---|
| 00:07 | 0:17:25 | `ui/README.md` | AP Desk review UI (M2 — agent C) |
| 00:14 | 0:17:32 | `ui/package.json` | UI dependencies and npm scripts (dev, build, lint, typecheck, test). |
| 00:23 | 0:17:41 | `ui/index.html` | Vite HTML entry point. |
| 00:30 | 0:17:48 | `ui/vite.config.ts` | Vite dev server/build config and Vitest setup. |
| 00:37 | 0:17:55 | `ui/tsconfig.json` | TypeScript compiler settings for the UI. |
| 00:44 | 0:18:03 | `ui/tsconfig.node.json` | TypeScript settings for Vite/Node config files. |
| 00:51 | 0:18:10 | `ui/eslint.config.js` | ESLint rules for the UI. |
| 00:59 | 0:18:17 | `ui/.gitignore` | UI build outputs ignored by git. |
| 01:06 | 0:18:24 | `ui/scripts/build-mock-data.mjs` | UI module: build-mock-data. |
| 01:15 | 0:18:33 | `ui/scripts/copy-fixtures.mjs` | UI module: copy-fixtures. |
| 01:22 | 0:18:40 | `ui/src/main.tsx` | UI module: main. |
| 01:29 | 0:18:47 | `ui/src/App.tsx` | UI module: App. |
| 01:36 | 0:18:54 | `ui/src/vite-env.d.ts` | / <reference types="vite/client" /> |
| 01:43 | 0:19:01 | `ui/src/styles/global.css` | CSS module styles for global. |
| 01:52 | 0:19:10 | `ui/src/api/types.ts` | openapi-typescript embeds JSON Schema $defs on some models; strip for app use. |
| 01:59 | 0:19:17 | `ui/src/api/client.ts` | UI module: client. |
| 02:13 | 0:19:31 | `ui/src/api/schema.d.ts` | Generated TypeScript types from openapi.yaml (npm run gen:api). |
| 02:26 | 0:19:44 | `ui/src/lib/invoiceEvents.ts` | UI module: invoiceEvents. |
| 02:33 | 0:19:51 | `ui/src/pages/ReviewQueuePage.tsx` | React component: ReviewQueuePage. |
| 02:42 | 0:20:00 | `ui/src/pages/ReviewQueuePage.module.css` | CSS module styles for ReviewQueuePage. |
| 02:49 | 0:20:07 | `ui/src/components/QueueTable.tsx` | React component: QueueTable. |
| 03:04 | 0:20:22 | `ui/src/components/QueueTable.module.css` | CSS module styles for QueueTable. |
| 03:15 | 0:20:33 | `ui/src/components/QueueTable.test.tsx` | Vitest tests for QueueTable. |
| 03:26 | 0:20:45 | `ui/src/components/DecisionBadge.tsx` | React component: DecisionBadge. |
| 03:34 | 0:20:52 | `ui/src/components/DecisionBadge.module.css` | CSS module styles for DecisionBadge. |
| 03:41 | 0:20:59 | `ui/src/components/MetricsStrip.tsx` | React component: MetricsStrip. |
| 03:50 | 0:21:08 | `ui/src/components/MetricsStrip.module.css` | CSS module styles for MetricsStrip. |
| 03:57 | 0:21:15 | `ui/src/pages/InvoiceDetailPage.tsx` | React component: InvoiceDetailPage. |
| 04:12 | 0:21:30 | `ui/src/pages/InvoiceDetailPage.module.css` | CSS module styles for InvoiceDetailPage. |
| 04:21 | 0:21:39 | `ui/src/pages/InvoiceDetailPage.errors.test.tsx` | Vitest tests for InvoiceDetailPage. |
| 04:34 | 0:21:52 | `ui/src/pages/InvoiceDetailPage.refresh.test.tsx` | Vitest tests for InvoiceDetailPage. |
| 04:48 | 0:22:06 | `ui/src/components/PdfViewer.tsx` | RenderingCancelledException or superseded render |
| 05:03 | 0:22:21 | `ui/src/components/PdfViewer.module.css` | CSS module styles for PdfViewer. |
| 05:12 | 0:22:30 | `ui/src/components/PdfViewer.test.tsx` | Vitest tests for PdfViewer. |
| 05:27 | 0:22:45 | `ui/src/components/BboxOverlay.tsx` | React component: BboxOverlay. |
| 05:38 | 0:22:56 | `ui/src/components/BboxOverlay.module.css` | CSS module styles for BboxOverlay. |
| 05:45 | 0:23:03 | `ui/src/components/IssuesPanel.tsx` | React component: IssuesPanel. |
| 05:54 | 0:23:12 | `ui/src/components/IssuesPanel.module.css` | CSS module styles for IssuesPanel. |
| 06:05 | 0:23:23 | `ui/src/components/CorrectionForm.tsx` | React component: CorrectionForm. |
| 06:19 | 0:23:37 | `ui/src/components/CorrectionForm.module.css` | CSS module styles for CorrectionForm. |
| 06:28 | 0:23:46 | `ui/src/components/ReviewActions.tsx` | React component: ReviewActions. |
| 06:37 | 0:23:55 | `ui/src/components/ReviewActions.module.css` | CSS module styles for ReviewActions. |
| 06:44 | 0:24:02 | `ui/src/components/PostToLedger.tsx` | React component: PostToLedger. |
| 06:53 | 0:24:11 | `ui/src/components/PostToLedger.module.css` | CSS module styles for PostToLedger. |
| 07:02 | 0:24:20 | `ui/src/components/PostToLedger.test.tsx` | Vitest tests for PostToLedger. |
| 07:11 | 0:24:30 | `ui/src/components/Toast/ToastContext.tsx` | React component: ToastContext. |
| 07:21 | 0:24:39 | `ui/src/components/Toast/Toast.module.css` | CSS module styles for Toast. |
| 07:30 | 0:24:48 | `ui/src/utils/bbox.ts` | PDF user-space bbox (bottom-left origin, points). |
| 07:41 | 0:24:59 | `ui/src/utils/bbox.test.ts` | Vitest tests for bbox. |
| 07:52 | 0:25:10 | `ui/src/utils/currency.ts` | Parse Indian-formatted amount string to number (lakhs grouping). |
| 07:59 | 0:25:17 | `ui/src/utils/currency.test.ts` | Vitest tests for currency. |
| 08:06 | 0:25:24 | `ui/src/utils/fields.ts` | UI module: fields. |
| 08:13 | 0:25:31 | `ui/src/utils/gstin.ts` | UI module: gstin. |
| 08:22 | 0:25:40 | `ui/src/utils/validation.ts` | UI module: validation. |
| 08:31 | 0:25:50 | `ui/src/utils/validation.test.ts` | Vitest tests for validation. |
| 08:39 | 0:25:57 | `ui/src/mock/browser.ts` | UI module: browser. |
| 08:46 | 0:26:04 | `ui/src/mock/handlers.ts` | UI module: handlers. |
| 08:57 | 0:26:15 | `ui/src/mock/store.ts` | UI module: store. |
| 09:12 | 0:26:30 | `ui/src/test/setup.ts` | UI module: setup. |
| 09:19 | 0:26:37 | `ui/src/mock/data.json` | Mock invoice data for the MSW offline UI mode. |
| 09:26 | 0:26:44 | `ui/public/mockServiceWorker.js` | Generated Mock Service Worker script. |

## Part 5 - BI, evals, datasets, tests, docs

`part5-bi-evals-tests-docs.mp4` - 15:04 (905 s), 18.7 MB, 89 files.

| Time | Cum. | File | Purpose |
|---|---|---|---|
| 00:07 | 0:27:00 | `bi/README.md` | Business intelligence (M4) |
| 00:16 | 0:27:09 | `bi/__init__.py` | Business intelligence exports and demo mart builder. |
| 00:23 | 0:27:17 | `bi/export.py` | Export tidy CSV marts from the AP Desk database. |
| 00:38 | 0:27:32 | `bi/mis.py` | Excel MIS workbook from exported CSV marts. |
| 00:53 | 0:27:47 | `bi/demo.py` | Build deterministic demo DB + CSV marts through the real pipeline. |
| 01:04 | 0:27:58 | `bi/data/vendors.csv` | BI data mart: vendors (5 rows). |
| 01:11 | 0:28:05 | `bi/data/issues.csv` | BI data mart: issues (22 rows). |
| 01:18 | 0:28:12 | `bi/data/eval_metrics.csv` | BI data mart: eval_metrics (14 rows). |
| 01:26 | 0:28:19 | `bi/data/invoices.csv` | BI data mart: invoices (50 rows). |
| 01:35 | 0:28:28 | `bi/data/line_items.csv` | BI data mart: line_items (103 rows). |
| 01:44 | 0:28:37 | `bi/data/ledger.csv` | BI data mart: ledger (32 rows). |
| 01:53 | 0:28:47 | `bi/data/receipts/1.json` | Sample JSON: 1. |
| 02:00 | 0:28:54 | `bi/powerbi/AravaliAP.pbip` | Power BI project entry file - open this in Power BI Desktop. |
| 02:07 | 0:29:01 | `bi/powerbi/.gitignore` | Ignores Power BI local cache files. |
| 02:14 | 0:29:08 | `bi/powerbi/AravaliAP.Report/definition.pbir` | Report definition pointing at the semantic model. |
| 02:21 | 0:29:15 | `bi/powerbi/AravaliAP.Report/report.json` | AP Overview report page layout and visuals. |
| 02:34 | 0:29:28 | `bi/powerbi/AravaliAP.SemanticModel/definition.pbism` | Semantic model definition file. |
| 02:42 | 0:29:35 | `bi/powerbi/AravaliAP.SemanticModel/definition/database.tmdl` | Power BI semantic model (TMDL): database. |
| 02:49 | 0:29:42 | `bi/powerbi/AravaliAP.SemanticModel/definition/model.tmdl` | Power BI semantic model (TMDL): model. |
| 02:56 | 0:29:50 | `bi/powerbi/AravaliAP.SemanticModel/definition/expressions.tmdl` | Power BI semantic model (TMDL): expressions. |
| 03:03 | 0:29:57 | `bi/powerbi/AravaliAP.SemanticModel/definition/relationships.tmdl` | Power BI semantic model (TMDL): relationships. |
| 03:20 | 0:30:14 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/EvalMetrics.tmdl` | Power BI semantic model (TMDL): EvalMetrics table - columns and measures. |
| 03:36 | 0:30:29 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/Invoices.tmdl` | Power BI semantic model (TMDL): Invoices table - columns and measures. |
| 03:49 | 0:30:43 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/Issues.tmdl` | Power BI semantic model (TMDL): Issues table - columns and measures. |
| 04:02 | 0:30:56 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/Ledger.tmdl` | Power BI semantic model (TMDL): Ledger table - columns and measures. |
| 04:20 | 0:31:13 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/LineItems.tmdl` | Power BI semantic model (TMDL): LineItems table - columns and measures. |
| 04:37 | 0:31:31 | `bi/powerbi/AravaliAP.SemanticModel/definition/tables/Vendors.tmdl` | Power BI semantic model (TMDL): Vendors table - columns and measures. |
| 04:46 | 0:31:40 | `bi/screenshots/ap-overview.png` | Screenshot: ap overview. |
| 05:04 | 0:31:57 | `bi/screenshots/mis-summary.png` | Screenshot: mis summary. |
| 05:11 | 0:32:04 | `bi/screenshots/powerbi-desktop-ap-overview.png` | Screenshot: powerbi desktop ap overview. |
| 05:34 | 0:32:28 | `evals/__init__.py` | (not shown - Quick Open picked bi/data/eval_metrics.csv here) package marker for evals. |
| 05:41 | 0:32:35 | `evals/__main__.py` | Package entry: use python -m evals.run or python -m evals.gate. |
| 05:48 | 0:32:42 | `evals/run.py` | CLI: python -m evals.run --pred <dir/truth> --truth <dir> --report <path> |
| 05:55 | 0:32:49 | `evals/thresholds.yaml` | Metric floors the eval gate enforces in CI. |
| 06:02 | 0:32:56 | `evals/baselines/offline-v1.json` | Baseline metrics for the offline extractor (n=50, seed=7). |
| 06:10 | 0:33:03 | `evals/normalize.py` | Field normalisation for metric comparison (see docs/metrics.md). |
| 06:19 | 0:33:12 | `evals/offline_predict.py` | Write ExtractedInvoice + Decision predictions via offline extract + validate. |
| 06:26 | 0:33:19 | `evals/metrics.py` | Compute evaluation metrics per docs/metrics.md. |
| 06:41 | 0:33:35 | `evals/gate.py` | CLI: python -m evals.gate [--report path] [--thresholds path] |
| 06:52 | 0:33:46 | `evals/agenteval_suite.py` | Bridge AP Desk metrics into AgentEval's RunReport (v0.5.0). |
| 07:03 | 0:33:57 | `evals/out/.gitignore` | Keeps eval report outputs out of git. |
| 07:16 | 0:34:10 | `datasets/__init__.py` | Dataset utilities and synthetic invoice generator. |
| 07:23 | 0:34:17 | `datasets/.gitignore` | Ignores generated synthetic datasets. |
| 07:31 | 0:34:24 | `datasets/synth/__init__.py` | Synthetic GST invoice PDF generator (v0). |
| 07:38 | 0:34:31 | `datasets/synth/__main__.py` | CLI: python -m datasets.synth --n 50 --seed 7 --out datasets/generated |
| 07:47 | 0:34:40 | `datasets/synth/types.py` | Shared synth layout types. |
| 07:54 | 0:34:48 | `datasets/synth/generator.py` | Deterministic Indian GST tax-invoice PDF + TruthRecord generator. |
| 08:09 | 0:35:03 | `datasets/synth/scanned.py` | Rasterise vector PDFs into mild scanned image-only PDFs (v1). |
| 08:22 | 0:35:16 | `datasets/sample/manifest.json` | List of the 9 sample invoices and their expected decisions. |
| 08:33 | 0:35:27 | `datasets/sample/vendor_master.json` | Vendor master data (GSTINs, names) used by validation. |
| 08:51 | 0:35:44 | `datasets/sample/11ce5dd2-b45e-d1f0-3139-d32c93cd59bf.truth.json` | Sample JSON: 11ce5dd2-b45e-d1f0-3139-d32c93cd59bf truth. |
| 09:12 | 0:36:06 | `tests/api/test_api_flow.py` | Tests: api flow. |
| 09:23 | 0:36:17 | `tests/api/test_cors.py` | Tests: cors. |
| 09:30 | 0:36:24 | `tests/api/test_errors.py` | Tests: errors. |
| 09:37 | 0:36:31 | `tests/api/test_openapi_contract.py` | Tests: openapi contract. |
| 09:44 | 0:36:38 | `tests/api/test_real_extract.py` | Tests: real extract. |
| 09:53 | 0:36:47 | `tests/bi/test_export.py` | Tests: export. |
| 10:03 | 0:36:56 | `tests/bi/test_mis.py` | Tests: mis. |
| 10:14 | 0:37:07 | `tests/bi/test_pbip.py` | Power Query columns not present in exported CSV headers. |
| 10:29 | 0:37:23 | `tests/contracts/test_ci_workflow.py` | Tests: ci workflow. |
| 10:38 | 0:37:32 | `tests/contracts/test_gstin.py` | Tests: gstin. |
| 10:45 | 0:37:39 | `tests/contracts/test_line_endings.py` | Tests: line endings. |
| 10:52 | 0:37:46 | `tests/contracts/test_openapi.py` | Tests: openapi. |
| 10:59 | 0:37:53 | `tests/contracts/test_schemas_export.py` | Tests: schemas export. |
| 11:06 | 0:38:00 | `tests/datasets/test_ci_workflow_d.py` | Tests: ci workflow d. |
| 11:13 | 0:38:07 | `tests/datasets/test_synth.py` | Tests: synth. |
| 11:29 | 0:38:22 | `tests/db/test_append_only.py` | Tests: append only. |
| 11:36 | 0:38:29 | `tests/e2e/test_api_e2e.py` | End-to-end API flow with real offline extraction. |
| 11:51 | 0:38:45 | `tests/evals/test_agenteval_suite.py` | Tests: agenteval suite. |
| 11:58 | 0:38:52 | `tests/evals/test_eval_run.py` | Tests: eval run. |
| 12:09 | 0:39:03 | `tests/extract/test_failure_paths.py` | Tests: failure paths. |
| 12:16 | 0:39:10 | `tests/extract/test_llm_mode.py` | Tests: llm mode. |
| 12:25 | 0:39:19 | `tests/extract/test_metrics.py` | Tests: metrics. |
| 12:37 | 0:39:30 | `tests/extract/test_ocr_scanned.py` | Tests: ocr scanned. |
| 12:46 | 0:39:39 | `tests/extract/test_sample_round_off.py` | Offline extract + validate for sample round_off_exceeded invoice. |
| 12:53 | 0:39:46 | `tests/hooks/test_scope_guard.py` | Table-driven tests for .cursor/hooks/scope_guard.py (real subprocess). |
| 13:08 | 0:40:02 | `tests/ingest/test_load_document.py` | Tests: load document. |
| 13:15 | 0:40:09 | `tests/ledger/test_posting.py` | Tests: posting. |
| 13:24 | 0:40:18 | `tests/ledger/test_verify.py` | Tests: verify. |
| 13:37 | 0:40:31 | `tests/validate/test_policy.py` | Table-driven tests for issue-code → decision outcome mapping. |
| 13:46 | 0:40:40 | `tests/validate/test_rules.py` | Focused validation rule tests (HSN, buyer GSTIN, round-off). |
| 13:55 | 0:40:49 | `tests/validate/test_synth_truth.py` | Tests: synth truth. |
| 14:09 | 0:41:02 | `docs/architecture.md` | Architecture (M2–M4) |
| 14:18 | 0:41:11 | `docs/multi-agent-build.md` | Multi-agent build harness |
| 14:29 | 0:41:23 | `docs/evaluation.md` | Evaluation (M2) |
| 14:36 | 0:41:30 | `docs/metrics.md` | Evaluation metrics (M2 — agent D) |
| 14:43 | 0:41:37 | `docs/release-notes-v0.1.0.md` | Aravali AP Desk v0.1.0 |
| 14:52 | 0:41:46 | `docs/proposals/README.md` | Contract change proposals |
| 14:59 | 0:41:53 | `docs/demo/aravali-demo.gif` | Animated GIF preview of the run demo. |

