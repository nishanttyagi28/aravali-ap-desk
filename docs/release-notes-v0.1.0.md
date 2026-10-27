# Aravali AP Desk v0.1.0

**Date:** 2026-10-27

Indian GST AP pipeline: PDF ingest → offline extract with bbox provenance → validate → **ALLOW / REVIEW / BLOCK** → review UI → sealed ledger stub → SQLite → Power BI + Excel MIS, with a blocking eval gate in CI.

## Highlights

- End-to-end offline path with no API keys required for CI
- FastAPI + React review UI with PDF bbox overlay
- Hash-chained ledger stub receipts and `ledger.verify`
- BI demo: CSV marts, `mis.xlsx`, Power BI PBIP (**AP Overview**)
- Multi-agent build with fail-closed scope hooks and frozen contracts after M1

## Metrics (offline v1, n=50, seed=7)

| Metric | Achieved | CI floor |
|--------|----------|----------|
| Header macro F1 | 1.00 | 0.98 |
| Line-item F1 | 1.00 | 0.98 |
| Bbox IoU@0.5 | 1.00 | 0.98 |
| Decision accuracy | 0.90 | 0.87 |

## How to run

```powershell
.\scripts\dev.ps1
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m bi.demo --out bi\data
```

Open `bi/powerbi/AravaliAP.pbip` in Power BI Desktop; set `DataFolder` to your `bi\data\` folder. See [README.md](../README.md) and [bi/README.md](../bi/README.md).

## Known limitations

- Ledger seal is a local stub, not production witnessing
- LLM extract is optional; offline is default
- Power BI needs Desktop + PBIP preview and machine-local CSV path
- Review UI screenshots for queue/detail not yet in repo

## Build harness

Sixteen logged agent runs through M4 (~**47.9M** SDK-reported tokens, ~**1,934** tool calls, ~**333** minutes). M3’s first attempt exceeded the 6M cap (**16.1M** tokens) before mid-run estimation was added; M4b required two supervisor-driven correction rounds against real Power BI Desktop. Details: [docs/multi-agent-build.md](multi-agent-build.md).

**Full changelog:** [CHANGELOG.md](../CHANGELOG.md)
