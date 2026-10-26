# Evaluation metrics (M2 — agent D)

This document specifies the AgentEval gate implemented in M2 using `nishanttyagi-agenteval` on PyPI.

## Prediction layout

For each invoice id `<id>` in a run directory:

| File | Content |
|------|---------|
| `<id>.json` | `ExtractedInvoice` prediction |
| `<id>.decision.json` | Optional `Decision` prediction |

Ground truth is `datasets/sample/<id>.truth.json` or generated `*.truth.json` (`TruthRecord`).

## Header field scoring

Per header field (e.g. `invoice_number`, `vendor_gstin`, `grand_total`, …):

1. **Normalise** before compare: GSTIN → uppercase; amounts → `Decimal` quantised to 2 dp; dates → ISO `YYYY-MM-DD`.
2. **Truth present, pred missing** → false negative (FN).
3. **Pred present, truth null** → false positive (FP).
4. **Both null** → ignored (no FP/FN).
5. **Both present but different** → FP + FN.

Report precision, recall, and F1 per field plus **macro F1** over included fields.

**Thresholds** are floors on **both** every per-field F1 and the macro F1 (configured in eval harness).

## Line items

Match predicted line items to truth **one-to-one** via Hungarian assignment on a cost matrix built from normalised `(description, hsn_sac, total)`. Score fields on matched pairs; unmatched lines count as FP/FN.

## Bounding boxes

For each truth key in `bboxes` (same keys as `ExtractedInvoice.fields`):

- **Hit** if predicted bbox exists on the **same page** and **IoU ≥ 0.5**.
- **Miss** if truth bbox exists but prediction has no bbox or IoU &lt; 0.5.

## Decision and issues

- **Decision accuracy**: `expected_decision` vs predicted `Decision.outcome`.
- **Per-issue-code confusion**: multiset of `IssueCode` on predicted `Decision.issues` vs `expected_issue_codes` in truth.

Report all metrics in CI artifacts; failing any configured floor fails the eval job.
