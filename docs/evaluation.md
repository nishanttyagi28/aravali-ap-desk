# Evaluation (M2)

Metrics are defined in [metrics.md](metrics.md) and implemented in `evals/metrics.py`.

## Reproduce locally

```powershell
cd E:\aravali-wt\D
.\.venv\Scripts\python -m pip install -e ".[dev,eval,synth]"
.\.venv\Scripts\python -m datasets.synth --n 50 --seed 7 --out datasets/generated
.\.venv\Scripts\python -m evals.run --pred truth --truth datasets/generated --report evals/out/report.json
.\.venv\Scripts\python -m evals.gate --report evals/out/report.json
```

Use a prediction directory with `<id>.json` (`ExtractedInvoice`) and optional `<id>.decision.json` (`Decision`). Pass `--pred truth` to score perfect predictions from truth invoices.

## Thresholds

Configured in `evals/thresholds.yaml` (floors = achieved minus margin; see `evals/baselines/offline-v1.json`).

| Metric | Offline v1 achieved (n=50, seed=7) | Floor |
|--------|-----------------------------------|-------|
| Per-header-field F1 | 1.00 | 0.98 |
| Header macro F1 | 1.00 | 0.98 |
| Line-item F1 | 1.00 | 0.98 |
| Bbox IoU@0.5 rate | 1.00 | 0.98 |
| Decision accuracy (offline extract + validate) | 0.90 | 0.87 |

`python -m evals.gate` exits non-zero and prints which metric failed.

## AgentEval bridge

`evals/agenteval_suite.py` maps the report into `agenteval.core.schema.RunReport`:

- `correctness_rate` ← header macro F1
- `provenance["aravali"]` ← full eval JSON

AgentEval has no native bbox / line-item / issue-confusion types; those metrics only appear under `provenance["aravali"]` (see module docstring).

## CI

The `evals` workflow job runs truth-as-prediction gate (blocking) and offline extraction + decision gate (blocking). The `ocr` job runs ingest/extract pytest and a report-only scanned eval (`--scanned-ratio 0.3`) when runtime allows.
