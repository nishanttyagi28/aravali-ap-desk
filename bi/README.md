# Business intelligence (M4)

CSV marts, Excel MIS, and a Power BI PBIP project for AP dashboards.

## Export marts

```powershell
.\.venv\Scripts\python -m bi.export --db data/ap_desk.db --out bi/data
.\.venv\Scripts\python -m bi.export --db data/ap_desk.db --eval-report evals/out/report.json --out bi/data
```

Writes UTF-8 CSVs with LF line endings and stable column order:

| File | Contents |
|------|----------|
| `invoices.csv` | Header totals, decision, top issue, posted flags |
| `line_items.csv` | Line-level GST and amounts |
| `issues.csv` | Validation issues per invoice |
| `ledger.csv` | Posted entries + seal / receipt chain fields |
| `vendors.csv` | Vendor master snapshot |
| `eval_metrics.csv` | Optional eval report metrics (`metric`, `field`, `value`, `run_id`) |

Amounts are plain decimal strings with two fractional digits.

## Deterministic demo

```powershell
.\.venv\Scripts\python -m bi.demo --out bi/data
```

Runs `datasets.synth` (`--n 50 --seed 7`) through ingest → extract → validate → post (every **ALLOW** invoice), exports CSVs, and builds `mis.xlsx`.

Demo artifacts: `bi/data/demo.db` (gitignored), `bi/data/receipts/<seq>.json`, and the CSV files above.

## Excel MIS

```powershell
.\.venv\Scripts\python -m bi.mis --data bi/data --out bi/data/mis.xlsx
.\.venv\Scripts\python -m bi.mis --data bi/data --out reports/ap_mis.xlsx --as-of 2026-10-26
```

Workbook sheets:

| Sheet | Purpose |
|-------|---------|
| **Summary** | Invoice counts by decision, grand total, posted amount, extraction macro F1 |
| **Aging** | Unposted invoices by age bucket (0–30 / 31–60 / 61–90 / >90 days vs `--as-of`) |
| **GST by rate** | Line-item pivot: `gst_rate` × taxable / CGST / SGST / IGST / cess |
| **Vendors** | Exposure (`grand_total`) and unposted amount by vendor |
| **Exceptions** | **REVIEW** / **BLOCK** rows grouped by `top_issue_code` |

Amount columns use Indian-style `#,##,##0.00`; header rows are frozen with autofilter.

## Power BI (PBIP)

Project path: `bi/powerbi/AravaliAP.pbip`

| Folder | Role |
|--------|------|
| `AravaliAP.SemanticModel/` | TMDL semantic model (CSV import) |
| `AravaliAP.Report/` | Legacy `report.json` report (**AP Overview** page) |

The model parameter **`DataFolder`** defaults to an absolute path with trailing backslash (`E:\aravali-ap-desk\bi\data\` in this clone). Power Query `File.Contents` requires that form on Windows. On another machine, use **Transform data → Edit parameters** and set `DataFolder` to your CSV folder (must end with `\`). Refresh after re-running `bi.export` or `bi.demo`.

### Open and refresh (Power BI Desktop)

1. Install Power BI Desktop (October 2024 or later).
2. Enable **Preview features** → **Power BI Project (.pbip) save option** (and TMDL if prompted).
3. Open `bi/powerbi/AravaliAP.pbip` (or `AravaliAP.Report/definition.pbir`).
4. If data does not load, **Transform data → Edit parameters** and point **DataFolder** at your `bi\data\` folder (trailing backslash).
5. **Home → Refresh** to reload CSVs.

CI validates JSON/TMDL wiring with `tests/bi/test_pbip.py`; it does not run Power BI Desktop.

## Sealed ledger verify

After posting, verify the hash-chained receipt stub:

```powershell
.\.venv\Scripts\python -m ledger.verify --db bi/data/demo.db
```

Exit `0` when intact; exit `1` with `BROKEN: receipt chain failed at seq=N` on tamper.
