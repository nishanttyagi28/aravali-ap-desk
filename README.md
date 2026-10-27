# Aravali AP Desk

Indian GST vendor invoices arrive as scanned PDFs and email attachments. Accounts payable teams still key invoice numbers, GSTINs, HSN lines, and CGST/SGST/IGST splits by hand. A single wrong GSTIN or tax regime mismatch blocks input tax credit (ITC); duplicate invoices slip through as double payments; month-end close waits on manual checks.

**Aravali AP Desk** is a Document AI pipeline that ingests PDFs, extracts structured fields with provenance (page + bounding box + confidence), validates against GST rules and your vendor master, and routes each invoice to **ALLOW**, **REVIEW**, or **BLOCK** before a sealed ledger post and AP dashboards.

## Architecture

```
  PDF upload
      |
      v
 +-----------+     +------------+     +-------------+
 |  Ingest   | --> |  Extract   | --> |  Validate   |
 | text/OCR  |     | rules/LLM  |     | GST + math  |
 +-----------+     +------------+     +------+------+
                                           |
                     +---------------------+---------------------+
                     |                     |                     |
                     v                     v                     v
                  ALLOW                 REVIEW                 BLOCK
                     |                     |                     |
                     v                     v                     v
              Ledger post            Human UI              Fix / reject
                     |
                     v
            SQLite / Postgres --> Power BI + Excel MIS
                     |
                     v
              AgentEval CI gate (field F1, decision accuracy)
```

**Decision policy (M3):** engine applies GSTIN checksum and state-code checks, CGST/SGST vs IGST consistency, line and total arithmetic, duplicate detection per vendor, and vendor-master match. Unknown vendor GSTIN → **REVIEW**; uncertain extraction (low confidence) or soft field gaps → **REVIEW**; hard GST/math/duplicate failures → **BLOCK** (`LINE_ARITHMETIC`, `TOTAL_MISMATCH` block). See `docai/validate/policy.py` and `docs/architecture.md`.

## Milestones

- [x] **M1 — Contracts** — Pydantic models, JSON Schema, OpenAPI stub, synthetic dataset, hooks, CI
- [ ] **M2 — Pipeline** — ingest, extract, validate, API, UI, evals (parallel agents A–D)
- [ ] **M3 — Review + ledger**
- [ ] **M4 — Marts + BI** (in progress: CSV export, MIS, sealed ledger stub)
- [ ] **M5 — Production hardening**

## Multi-agent build

Roles **A / B / C / D** own directories listed in `AGENTS.md`. **Cursor hooks** (`.cursor/hooks.json`) run `scope_guard.py` on every edit and shell command: worker agents cannot touch frozen contracts, cannot commit, and cannot install arbitrary packages. Default extraction mode is **offline** (no API keys in CI).

## Quickstart

### One-command dev (API + UI)

**Windows**

```powershell
cd E:\aravali-ap-desk
.\scripts\dev.ps1
```

Opens the API on `http://127.0.0.1:8000` and Vite on `http://127.0.0.1:5173` (real offline extractor, not MSW). Seeds `datasets/sample` into `data/ap_desk.db` idempotently.

**Linux / macOS**

```bash
cd aravali-ap-desk
make dev
```

### Tests and eval

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev,eval,synth,ocr]"
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m datasets.synth --n 50 --seed 7 --out datasets\generated
make eval   # or: python -m evals.run ... && python -m evals.gate
```

### Windows (Python 3.12, manual)

```powershell
cd E:\aravali-ap-desk
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
```

### Linux (manual)

```bash
make install
make test
```

Copy `.env.example` to `.env` for optional LLM mode (`EXTRACT_MODE=llm`, `GROQ_API_KEY`).

### BI export and demo (M4)

```powershell
.\.venv\Scripts\python -m bi.export --db data\ap_desk.db --out bi\data
.\.venv\Scripts\python -m bi.demo --out bi\data
```

`bi.demo` runs the synthetic pipeline (`--n 50 --seed 7`), posts every **ALLOW** invoice, writes CSV marts under `bi/data`, and builds `bi/data/mis.xlsx`. Open `bi/powerbi/AravaliAP.pbip` in Power BI Desktop (PBIP preview) or run `python -m bi.mis --data bi/data --out mis.xlsx`. See `bi/README.md` for CSV columns, MIS sheets, and refresh steps.

### Sealed ledger verify (M4 stub)

Each ledger post appends a hash-chained KarmaSakshi-style **stub** receipt (`ledger/receipt.py`) and fills `SealRef` on the API post response (`provider: stub`, `witness_status: local`).

```powershell
.\.venv\Scripts\python -m ledger.verify --db bi\data\demo.db
```

Exit code `0` when the chain is intact; `1` with the first broken `seq` after tamper.

## License

MIT — see [LICENSE](LICENSE).
