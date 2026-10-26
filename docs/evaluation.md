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

Configured in `evals/thresholds.yaml`:

| Metric | Floor |
|--------|-------|
| Per-header-field F1 | 0.90 |
| Header macro F1 | 0.90 |
| Line-item F1 | 0.90 |
| Bbox IoU@0.5 rate | 0.85 |
| Decision accuracy (when decisions present) | 0.95 |

`python -m evals.gate` exits non-zero and prints which metric failed.

## AgentEval bridge

`evals/agenteval_suite.py` maps the report into `agenteval.core.schema.RunReport`:

- `correctness_rate` ← header macro F1
- `provenance["aravali"]` ← full eval JSON

AgentEval has no native bbox / line-item / issue-confusion types; those metrics only appear under `provenance["aravali"]` (see module docstring).

## CI

The `evals` workflow job runs truth-as-prediction gate (blocking) and offline extraction gate (report-only with `continue-on-error: true` until M3).
