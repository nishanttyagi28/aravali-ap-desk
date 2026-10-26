"""Bridge AP Desk metrics into AgentEval's RunReport (v0.5.0).

AgentEval's first-class metrics target LLM agent runs (correctness, hallucination,
tools, latency, cost). This module maps our document-extraction report into a
RunReport so CI can store a familiar artifact shape:

- ``correctness_rate`` := header macro F1 (when present)
- ``provenance["aravali"]`` := full ``evals.metrics`` summary + per-field scores

Gap: AgentEval has no native schema for bbox IoU, line-item Hungarian F1, or
issue-code confusion; those live only under ``provenance["aravali"]``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.metrics import compute_report


def build_run_report(
    pred_dir: Path | str,
    truth_dir: Path,
    *,
    adapter: str = "aravali_extract",
) -> Any:
    from agenteval.core.schema import CaseResult, RunReport
    from agenteval.core.store import get_git_sha

    report = compute_report(pred_dir, truth_dir)
    summary = report.get("summary") or {}
    macro_f1 = summary.get("header_macro_f1")

    case_results: list[CaseResult] = []
    for row in report.get("per_invoice") or []:
        fields = row.get("header_fields") or {}
        f1s = [v["f1"] for v in fields.values() if v.get("f1") is not None]
        case_f1 = sum(f1s) / len(f1s) if f1s else None
        passed = case_f1 is not None and case_f1 >= 0.99
        case_results.append(
            CaseResult(
                case_id=row["invoice_id"],
                prompt=f"extract:{row['invoice_id']}",
                final_answer="",
                correctness_pass=passed,
                status="passed" if passed else "failed",
            )
        )

    return RunReport(
        run_id=f"aravali-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat(),
        git_sha=get_git_sha(),
        adapter=adapter,
        case_results=case_results,
        correctness_rate=macro_f1,
        provenance={"aravali": report},
    )


def write_agenteval_report(
    pred_dir: Path | str,
    truth_dir: Path,
    out_path: Path,
) -> dict[str, Any]:
    run = build_run_report(pred_dir, truth_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        __import__("json").dumps(run.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run.to_dict()
