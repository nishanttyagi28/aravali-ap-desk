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

**Decision policy (M2+):** engine applies GSTIN checksum and state-code checks, CGST/SGST vs IGST consistency, line and total arithmetic, duplicate detection per vendor, and vendor-master match. Uncertain extraction (low confidence) or soft issues → REVIEW; hard failures → BLOCK.

## Milestones

- [x] **M1 — Contracts** — Pydantic models, JSON Schema, OpenAPI stub, synthetic dataset, hooks, CI
- [ ] **M2 — Pipeline** — ingest, extract, validate, API, UI, evals (parallel agents A–D)
- [ ] **M3 — Review + ledger**
- [ ] **M4 — Marts + BI**
- [ ] **M5 — Production hardening**

## Multi-agent build

Roles **A / B / C / D** own directories listed in `AGENTS.md`. **Cursor hooks** (`.cursor/hooks.json`) run `scope_guard.py` on every edit and shell command: worker agents cannot touch frozen contracts, cannot commit, and cannot install arbitrary packages. Default extraction mode is **offline** (no API keys in CI).

## Quickstart

### Windows (Python 3.12)

```powershell
cd E:\aravali-ap-desk
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m datasets.synth --n 50 --seed 7 --out datasets\generated
```

### Linux

```bash
cd aravali-ap-desk
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
```

Copy `.env.example` to `.env` for optional LLM mode (`EXTRACT_MODE=llm`, `GROQ_API_KEY`).

## License

MIT — see [LICENSE](LICENSE).
