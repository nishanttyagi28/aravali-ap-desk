# Architecture (M2)

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
