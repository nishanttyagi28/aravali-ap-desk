# Business intelligence (M4)

CSV marts and Excel MIS for AP dashboards (Power BI / finance ops).

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

Demo artifacts: `bi/data/demo.db`, `bi/data/receipts/<seq>.json`, and the CSV files above.

## Excel MIS

`bi/mis.py` loads the exported CSVs into workbook sheets: **Invoices**, **LineItems**, **Issues**, **Ledger**, **Vendors**, **EvalMetrics**.

## Power BI

Point Power BI Desktop at `bi/data/*.csv` (or import `mis.xlsx`). Typical visuals: vendor spend, block/review rates, GST issue trends, posted ledger totals. CI does not run Power BI; validate reports locally.

## Sealed ledger verify

After posting, verify the hash-chained receipt stub:

```powershell
.\.venv\Scripts\python -m ledger.verify --db bi/data/demo.db
```

Exit `0` when intact; exit `1` with `BROKEN: receipt chain failed at seq=N` on tamper.
