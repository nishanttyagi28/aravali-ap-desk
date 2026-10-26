# Architecture (M2–M4)

## Pipeline

```text
PDF upload → ingest (load_document) → extract (offline / LLM) → validate → decide → ledger / API
```

Synthetic evaluation uses the same contracts end-to-end: `TruthRecord` ground truth, `ExtractedInvoice` predictions, optional `Decision` predictions.

## Data contracts

| Artifact | Role |
|----------|------|
| `ExtractedInvoice` | Structured header, line items, per-field provenance |
| `TruthRecord` | Expected invoice, decision, issue codes, layout bboxes |
| `Decision` | Engine outcome + `ValidationIssue` list |
| `VendorMaster` | Known vendors for GSTIN/state checks |

### BBox coordinate convention

Bounding boxes use **PDF user space of the unrotated page**: units are **points**, origin **bottom-left**, **y** increases upward (reportlab / pypdf). Tools that emit top-left coordinates (pdfplumber `top`/`bottom`, OCR pixels) must convert: `y0 = page_height - bottom`, `y1 = page_height - top`.

Synth v1 scanned PDFs apply a mild page rotation; truth `bboxes` are updated with the same transform so eval IoU remains in canonical page space.

## Decision policy

| Outcome | Issue codes (representative) |
|---------|----------------------------|
| **ALLOW** | (none) |
| **BLOCK** | `GSTIN_CHECKSUM`, `GSTIN_STATE_MISMATCH`, `TAX_REGIME_MISMATCH`, `DUPLICATE_INVOICE`, `LINE_ARITHMETIC`, `TOTAL_MISMATCH` |
| **REVIEW** | `VENDOR_UNKNOWN`, `ROUND_OFF_EXCEEDED`, `LOW_CONFIDENCE`, `MISSING_FIELD` |

Policy implementation: `docai/validate/policy.py` (`BLOCK_CODES`, `REVIEW_CODES`, `outcome_from_issues`).

## Trust boundaries

- **Offline extraction** is the CI default (no API keys).
- **LLM mode** is opt-in and must not be required for gate jobs.
- **Supervisor** is the only actor that commits; agents run under `AGENT_ROLE` scope hooks.

## Ledger seal (M4 stub)

Each successful `post_invoice` appends:

1. A **ledger entry** row (append-only SQLite triggers on `ledger_entries`).
2. A **receipt** row in `ledger_receipts` plus optional mirror `data/receipts/<seq>.json`.

Receipt canonical JSON (sorted keys, no whitespace, UTF-8) includes `entry_id`, `invoice_id`, `vendor_id`, `amounts`, `posted_at`, `prev_receipt_sha256`, and `seq`. `receipt_sha256 = sha256(canonical)`; genesis `prev_receipt_sha256` is 64 ASCII zeros. The entry’s `SealRef` uses provider `stub`, `commit_id` and `manifest_sha256` equal to the receipt hash, `witness_status` `local`.

`python -m ledger.verify --db <path>` walks receipts in `seq` order, recomputes hashes, checks prev links, and cross-checks ledger entry amounts and seal fields. Non-zero exit names the first broken `seq`.

## BI marts (M4)

`bi.export` projects the operational DB into tidy CSVs for Power BI and `bi/mis` Excel workbooks. `bi.demo` builds a deterministic SQLite mart from the synthetic generator through the real pipeline (seed 7, n 50) for CI smoke and local dashboards.
