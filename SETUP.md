# Run Aravali AP Desk on a new machine

Everything needed to run the project is in this repo. Generated files (venv, `node_modules`, SQLite DBs, synthetic PDFs, eval reports) are rebuilt by the commands below. Verified on a fresh clone on Windows 11 on 2026-10-27.

## Prerequisites

| Tool | Version | Needed for |
|------|---------|------------|
| Git | any recent | clone |
| Python | **3.12.x** (`py -3.12` on Windows) | pipeline, API, tests, BI export |
| Node.js | **22+** (CI uses 22; 24 also works) | Review UI |
| Power BI Desktop | Oct 2024+ with PBIP preview enabled | optional: open `bi/powerbi/AravaliAP.pbip` |
| Excel | any | optional: open `bi/data/mis.xlsx` |

No Tesseract or system OCR install is needed: OCR uses the pip package `rapidocr-onnxruntime` (extra `[ocr]`, optional; the default offline extractor reads the PDF text layer). No API keys are needed; offline extraction is the default.

## 1. Clone and install (PowerShell)

```powershell
git clone https://github.com/nishanttyagi28/aravali-ap-desk.git
cd aravali-ap-desk
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-lock.txt   # exact versions (optional)
.\.venv\Scripts\python -m pip install -e ".[dev,synth,eval]"      # add ,ocr for scanned PDFs
Copy-Item .env.example .env                                       # optional; only for EXTRACT_MODE=llm
```

Linux/macOS: `python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev,synth,eval]"` (or `make install`).

## 2. Tests and eval gate

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m datasets.synth --n 50 --seed 7 --scanned-ratio 0 --out datasets\generated
.\.venv\Scripts\python -m evals.run --pred truth --truth datasets\generated --report evals\out\report-smoke.json
.\.venv\Scripts\python -m evals.gate --report evals\out\report-smoke.json
```

## 3. Seed the dev database

```powershell
New-Item -ItemType Directory -Force data | Out-Null
$env:DATABASE_URL = "sqlite:///data/ap_desk.db"
.\.venv\Scripts\python -m api.seed      # idempotent; loads datasets/sample into data/ap_desk.db
```

`data/` is gitignored on purpose: the seed command recreates it.

## 4. Run the API + Review UI

One command (seeds the DB, starts API on :8000 and Vite UI on :5173):

```powershell
.\scripts\dev.ps1
```

Or manually, in two terminals:

```powershell
$env:DATABASE_URL = "sqlite:///data/ap_desk.db"; .\.venv\Scripts\python -m api.serve
cd ui; npm ci; $env:VITE_API_BASE = "http://127.0.0.1:8000"; npm run dev -- --host 127.0.0.1
```

UI checks: `cd ui; npm run lint; npm run typecheck; npx vitest --run; npm run build`.

## 5. Demo pipeline, sealed ledger, BI marts, Excel MIS

```powershell
.\.venv\Scripts\python -m bi.demo --out bi\data          # 50 synthetic invoices -> demo.db, CSV marts, mis.xlsx
.\.venv\Scripts\python -m ledger.verify --db bi\data\demo.db   # exit 0 = hash chain intact
```

`bi.demo` rewrites the committed `bi/data/*.csv`, `receipts/*.json` and `mis.xlsx` with fresh timestamps; `git checkout -- bi/data` restores the committed snapshot.

## 6. Power BI

1. Open `bi/powerbi/AravaliAP.pbip` in Power BI Desktop.
2. **Transform data -> Edit parameters**: set **DataFolder** to the full path of your `bi\data\` folder, with a trailing `\` (the committed value is `E:\aravali-ap-desk\bi\data\`).
3. **Home -> Refresh**. Details: [bi/README.md](bi/README.md).

## What is intentionally not in git

| Path | Why | Recreate with |
|------|-----|---------------|
| `.venv/`, `ui/node_modules/` | dependencies | step 1, `npm ci` |
| `data/` (`ap_desk.db`, uploads, receipts) | local dev DB | step 3 |
| `bi/data/demo.db` | generated demo DB | step 5 |
| `datasets/generated/` | synthetic invoices (deterministic, seed 7) | step 2 |
| `evals/out/*.json` | eval reports | step 2 (CI also uploads them as artifacts) |
| `ui/dist/`, caches | build output | `npm run build` |
| `.env` | secrets | copy `.env.example` |

## Build harness (optional)

The Cursor SDK multi-agent harness that built this repo (runner, budgets, scope checks, approval gates, every prompt and run log) lives in the **private** repo [nishanttyagi28/aravali-supervisor](https://github.com/nishanttyagi28/aravali-supervisor); its README has its own setup steps (`npm ci`, `CURSOR_API_KEY` user env var). The VS Code tasks in `.vscode/tasks.json` call it at `E:\aravali-supervisor`.