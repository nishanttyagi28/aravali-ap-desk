"""Compute evaluation metrics per docs/metrics.md."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docai.contracts.bbox import BBox
from docai.contracts.decision import Decision
from docai.contracts.extracted import ExtractedInvoice, LineItem
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode
from evals.normalize import HEADER_FIELDS, values_match


def bbox_iou(a: BBox, b: BBox) -> float:
    if a.page != b.page:
        return 0.0
    ix0 = max(a.x0, b.x0)
    iy0 = max(a.y0, b.y0)
    ix1 = min(a.x1, b.x1)
    iy1 = min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 0.0


def _prf(tp: int, fp: int, fn: int) -> dict[str, float | None]:
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = None if prec is None or rec is None or (prec + rec) == 0 else 2 * prec * rec / (prec + rec)
    return {"precision": prec, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def score_header_fields(truth: TruthRecord, pred: ExtractedInvoice) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in HEADER_FIELDS:
        t_val = getattr(truth.invoice, name)
        p_val = getattr(pred, name)
        tp = fp = fn = 0
        if t_val is None and p_val is None:
            pass
        elif t_val is None and p_val is not None:
            fp = 1
        elif t_val is not None and p_val is None:
            fn = 1
        elif values_match(name, t_val, p_val):
            tp = 1
        else:
            fp = 1
            fn = 1
        out[name] = _prf(tp, fp, fn)
    return out


def _line_dict(item: LineItem) -> dict[str, Any]:
    return {
        "description": item.description,
        "hsn_sac": item.hsn_sac,
        "total": item.total,
    }


def _hungarian(cost: list[list[float]]) -> list[int]:
    """Min-cost assignment; returns col index per row."""
    n = len(cost)
    if n == 0:
        return []
    if n == 1:
        return [0]
    # Small n only (invoice line items); brute force for n <= 8 else greedy
    if n <= 8:
        from itertools import permutations

        best: list[int] | None = None
        best_cost = float("inf")
        for perm in permutations(range(n)):
            c = sum(cost[i][perm[i]] for i in range(n))
            if c < best_cost:
                best_cost = c
                best = list(perm)
        return best or list(range(n))
    return [min(range(n), key=lambda j: cost[i][j]) for i in range(n)]


def _line_cost(truth_line: dict[str, Any], pred_line: dict[str, Any]) -> float:
    mismatches = sum(
        1
        for f in ("description", "hsn_sac", "total")
        if not values_match(f, truth_line.get(f), pred_line.get(f))
    )
    return float(mismatches)


def score_line_items(truth: TruthRecord, pred: ExtractedInvoice) -> dict[str, Any]:
    truth_lines = [_line_dict(li) for li in truth.invoice.line_items]
    pred_lines = [_line_dict(li) for li in pred.line_items]
    nt, np_ = len(truth_lines), len(pred_lines)
    if nt == 0 and np_ == 0:
        return {**_prf(0, 0, 0), "matched": 0}

    size = max(nt, np_)
    big = 10_000.0
    matrix: list[list[float]] = []
    for i in range(size):
        row: list[float] = []
        for j in range(size):
            if i >= nt and j >= np_:
                row.append(0.0)
            elif i >= nt or j >= np_:
                row.append(big)
            else:
                row.append(_line_cost(truth_lines[i], pred_lines[j]))
        matrix.append(row)
    assign = _hungarian(matrix)
    tp = fp = fn = 0
    matched = 0
    used_pred: set[int] = set()
    for i in range(nt):
        j = assign[i]
        if j >= np_:
            fn += 1
            continue
        used_pred.add(j)
        if _line_cost(truth_lines[i], pred_lines[j]) == 0.0:
            tp += 1
            matched += 1
        else:
            fp += 1
            fn += 1
    fp += np_ - len(used_pred)
    return {**_prf(tp, fp, fn), "matched": matched}


def score_bboxes(truth: TruthRecord, pred: ExtractedInvoice) -> dict[str, Any]:
    hits = misses = 0
    for key, truth_bbox in truth.bboxes.items():
        field = pred.fields.get(key)
        pred_bbox = field.bbox if field is not None else None
        if pred_bbox is None:
            misses += 1
            continue
        if bbox_iou(pred_bbox, truth_bbox) >= 0.5:
            hits += 1
        else:
            misses += 1
    total = hits + misses
    rate = hits / total if total else 1.0
    return {"hits": hits, "misses": misses, "total": total, "iou_at_0_5_rate": rate}


def _issue_multiset(codes: list[IssueCode]) -> Counter[str]:
    return Counter(str(c) for c in codes)


def score_decision(truth: TruthRecord, decision: Decision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    outcome_correct = decision.outcome == truth.expected_decision
    truth_issues = _issue_multiset(truth.expected_issue_codes)
    pred_issues = _issue_multiset([i.code for i in decision.issues])
    all_codes = sorted(set(truth_issues) | set(pred_issues))
    per_code: dict[str, dict[str, int]] = {}
    for code in all_codes:
        per_code[code] = {
            "truth": truth_issues.get(code, 0),
            "pred": pred_issues.get(code, 0),
        }
    return {
        "outcome_correct": outcome_correct,
        "expected_outcome": str(truth.expected_decision),
        "predicted_outcome": str(decision.outcome),
        "issue_code_counts": per_code,
    }


@dataclass
class EvalInputs:
    invoice_id: str
    truth: TruthRecord
    pred: ExtractedInvoice
    decision: Decision | None


def evaluate_one(inp: EvalInputs) -> dict[str, Any]:
    fields = score_header_fields(inp.truth, inp.pred)
    lines = score_line_items(inp.truth, inp.pred)
    bboxes = score_bboxes(inp.truth, inp.pred)
    decision = score_decision(inp.truth, inp.decision)
    return {
        "invoice_id": inp.invoice_id,
        "header_fields": fields,
        "line_items": lines,
        "bboxes": bboxes,
        "decision": decision,
    }


def macro_f1(field_scores: dict[str, dict[str, Any]]) -> float | None:
    f1s = [s["f1"] for s in field_scores.values() if s.get("f1") is not None]
    if not f1s:
        return None
    return sum(f1s) / len(f1s)


def aggregate(per_invoice: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_invoice:
        return {"count": 0}

    field_tp = dict.fromkeys(HEADER_FIELDS, 0)
    field_fp = dict.fromkeys(HEADER_FIELDS, 0)
    field_fn = dict.fromkeys(HEADER_FIELDS, 0)
    line_tp = line_fp = line_fn = 0
    bbox_hits = bbox_total = 0
    decision_correct = decision_total = 0
    issue_agg: dict[str, dict[str, int]] = {}

    for row in per_invoice:
        for name in HEADER_FIELDS:
            s = row["header_fields"][name]
            field_tp[name] += int(s["tp"])
            field_fp[name] += int(s["fp"])
            field_fn[name] += int(s["fn"])
        ls = row["line_items"]
        line_tp += int(ls["tp"])
        line_fp += int(ls["fp"])
        line_fn += int(ls["fn"])
        bb = row["bboxes"]
        bbox_hits += int(bb["hits"])
        bbox_total += int(bb["total"])
        dec = row.get("decision")
        if dec is not None:
            decision_total += 1
            if dec["outcome_correct"]:
                decision_correct += 1
            for code, counts in dec.get("issue_code_counts", {}).items():
                bucket = issue_agg.setdefault(code, {"truth": 0, "pred": 0})
                bucket["truth"] += counts["truth"]
                bucket["pred"] += counts["pred"]

    header_fields = {
        name: _prf(field_tp[name], field_fp[name], field_fn[name]) for name in HEADER_FIELDS
    }
    line_items = _prf(line_tp, line_fp, line_fn)
    bbox_rate = bbox_hits / bbox_total if bbox_total else 1.0
    decision_accuracy = decision_correct / decision_total if decision_total else None

    return {
        "count": len(per_invoice),
        "header_fields": header_fields,
        "header_macro_f1": macro_f1(header_fields),
        "line_items": line_items,
        "bboxes": {
            "hits": bbox_hits,
            "total": bbox_total,
            "iou_at_0_5_rate": bbox_rate,
        },
        "decision_accuracy": decision_accuracy,
        "decision_count": decision_total,
        "issue_code_confusion": issue_agg,
    }


def load_truth_dir(truth_dir: Path) -> dict[str, TruthRecord]:
    out: dict[str, TruthRecord] = {}
    for path in sorted(truth_dir.glob("*.truth.json")):
        invoice_id = path.stem.removesuffix(".truth")
        out[invoice_id] = TruthRecord.model_validate_json(path.read_text(encoding="utf-8"))
    return out


def load_predictions(
    pred_dir: Path | str, truths: dict[str, TruthRecord]
) -> dict[str, tuple[ExtractedInvoice, Decision | None]]:
    if str(pred_dir) == "truth":
        return {tid: (tr.invoice, None) for tid, tr in truths.items()}

    root = Path(pred_dir)
    out: dict[str, tuple[ExtractedInvoice, Decision | None]] = {}
    for tid in truths:
        pred_path = root / f"{tid}.json"
        if not pred_path.is_file():
            continue
        pred = ExtractedInvoice.model_validate_json(pred_path.read_text(encoding="utf-8"))
        dec_path = root / f"{tid}.decision.json"
        decision = None
        if dec_path.is_file():
            decision = Decision.model_validate_json(dec_path.read_text(encoding="utf-8"))
        out[tid] = (pred, decision)
    return out


def compute_report(pred_dir: Path | str, truth_dir: Path) -> dict[str, Any]:
    truths = load_truth_dir(truth_dir)
    preds = load_predictions(pred_dir, truths)
    per_invoice: list[dict[str, Any]] = []
    missing_preds: list[str] = []

    for tid, truth in sorted(truths.items()):
        if tid not in preds:
            missing_preds.append(tid)
            continue
        pred, decision = preds[tid]
        per_invoice.append(
            evaluate_one(EvalInputs(invoice_id=tid, truth=truth, pred=pred, decision=decision))
        )

    summary = aggregate(per_invoice)
    return {
        "pred_source": str(pred_dir),
        "truth_dir": str(truth_dir),
        "missing_predictions": missing_preds,
        "per_invoice": per_invoice,
        "summary": summary,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
