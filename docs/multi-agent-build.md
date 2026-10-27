# Multi-agent build harness

Aravali AP Desk v0.1.0 was built with a **human-controlled supervisor** driving Cursor agents in scoped worktrees. The supervisor does **not** edit product code in the repo; it sets `AGENT_ROLE`, runs agents, enforces budgets, runs an independent scope check, runs the quality gate, and commits with approval trailers. Agents never `git commit` or `git push`.

## Roles and ownership

| Role | Responsibility |
|------|----------------|
| **A** | Ingest + extract (`docai/ingest/`, `docai/extract/`) |
| **B** | Validate + API + ledger + DB |
| **C** | Review UI (`ui/`) |
| **D** | Datasets, evals, CI, BI, docs |
| **lead** | Integration on `main`, frozen contract edits with process |
| **supervisor** | Commits, git hooks, `.vscode/` (supervisor-only paths) |

Single source of truth: `AGENTS.md` and `.cursor/hooks/ownership.json`. After **M1**, contracts are **frozen** (`frozenActive=true` in ownership): `schemas/**`, `openapi.yaml`, `pyproject.toml`, `AGENTS.md`, `.cursor/**`, `docai/contracts/**`, `scripts/**`, and related paths require lead/supervisor + `contract-change` on PRs.

## Fail-closed Cursor hooks

`.cursor/hooks.json` invokes `scope_guard.py` on:

- **`preToolUse`** — Write/Edit/StrReplace/Delete/NotebookEdit; denies paths outside the role allowlist, frozen paths for workers, and supervisor-only trees.
- **`beforeShellExecution`** — denies git writes for workers, destructive commands, and out-of-scope installs.

Rule IDs surfaced to agents: **`AAD-SCOPE-000`** through **`AAD-SCOPE-005`**, **`AAD-SHELL-001`** through **`AAD-SHELL-003`**. Unset or unknown `AGENT_ROLE` → deny everything.

### What the controls caught in practice

| Incident | Control / fix |
|----------|----------------|
| **`git -C . commit` bypass** (M1 review) | Shell hook expanded to block git write variants, not only bare `git commit`. |
| **CRLF schema drift on Linux CI** | Normalized line endings / generator output; gate on Linux in CI. |
| **Duplicate `env:` key in workflow YAML** | CI review; valid single mapping per job. |
| **Job-level `hashFiles` in invalid workflow** | Workflow schema fix in D’s CI pass. |
| **Dev-only install collection failure** | Optional dependency groups aligned with `pip install -e ".[dev]"` in gate venv. |
| **M3 token overrun (16.1M SDK tokens)** | Per-run cap was 6M but usage reported only at run end → **mid-run estimator** (since 2026-10-26) cancels early; M3 correction run finished at ~4.0M tokens. |
| **M4a cancel at 166 tool calls** | Same estimator (~220 × tool_calls² ≈ 6.06M estimate); no end-of-run SDK row. |
| **Scope escapes** | `preToolUse` path normalization on Windows vs POSIX; independent `check-scope.ts` on staged diff before supervisor commit. |

## Independent supervisor scope check

Repo hooks protect the agent session; the supervisor also runs a **git-diff ownership check** (`check-scope.ts <role> [--staged]`) against its copy of allowlists. This caught staged edits that agents believed were in-scope when path resolution differed. Pre-commit on the supervisor worktree runs the same check.

## Quality gate

After each agent run, `gate.ts` (supervisor) runs in the **worktree venv**:

```text
ruff check .
ruff format --check .
python -m pytest -q
```

Approve-and-push **refuses** on scope or gate failure. M1–M5 were **auto-approved** by owner policy with the decision logged; human `approve` remains the default for other work.

## Budgets and correction rounds

| Limit | Value |
|-------|--------|
| Per-run tokens (SDK total) | 6M (enforced mid-run by estimate after M3 incident) |
| Per-run tool calls | 400 |
| Per-run wall clock | 60 minutes |
| Per-day tokens | 80M (raised from 40M by owner) |
| Correction rounds per step/role | 2 max |

**Token accounting:** Cursor SDK `totalTokens` = input + output + cache read; input already includes cache reads, so the sum **double-counts** cache for budgeting. For billable-ish totals, use input + output only.

## Worktrees and merge-to-main (M2)

Parallel M2 agents used **one `.venv` per worktree** (never shared). Supervisor merged role branches with **`git merge --no-ff`**, ran the gate on **merged main**, and **rolled back** on failure.

Recorded merges: M1 `27f6465` + `d3678db`; M2-B `ead13c4` → `e67cdba`, M2-A `6940634` → `2b7b8dc`, M2-B fix `eaabf52` → `d0ce34c`, M2-D `8214051`+`370f54f` → `956d49c`, M2-C `bd64b9b` → `cbad1e2`; M3 `0da8665`; M4a `9ea58ca`.

## Run ledger

Each harness invocation appends to supervisor `logs/runs.jsonl`: agent id, run id, model, prompt hash, token breakdown, duration, files touched, gate result, approval/refusal events.

### Harness runs (M1–M4; M5 docs not logged here)

| # | step | role | correction | status | total tokens (SDK) | tool calls | minutes | gate |
|---|------|------|------------|--------|-------------------|------------|---------|------|
| 1 | M1 | lead | False | finished | 2552137 | 155 | 12.9 | pass |
| 2 | M1 | lead | True | finished | 2192321 | 63 | 6.7 | pass |
| 3 | M1 | lead | True | finished | 2355730 | 34 | 3.7 | pass |
| 4 | M2 | A | False | finished | 2296750 | 113 | 18.5 | pass |
| 5 | M2 | B | False | finished | 2240020 | 216 | 25.4 | pass |
| 6 | M2 | D | False | finished | 5049479 | 182 | 25.7 | pass |
| 7 | M2 | C | False | finished | 2943539 | 251 | 29.3 | pass |
| 8 | M2 | B | True | finished | 1492315 | 73 | 18.6 | pass |
| 9 | M2 | D | True | finished | 1085702 | 93 | 30.7 | pass |
| 10 | M2 | D | True | finished | 809304 | 22 | 9 | pass |
| 11 | M3 | lead | False | cancelled | 16109745 | 315 | 45.9 | skipped |
| 12 | M3 | lead | True | finished | 4009978 | 41 | 14.3 | pass |
| 13 | M4 | lead | False | cancelled | ~ (est., cancelled) | 166 | 23.6 | skipped |
| 14 | M4 | lead | False | finished | 2728994 | 100 | 32.3 | pass |
| 15 | M4 | lead | True | killed by owner pause (no ledger row) | n/a | ~7 | ~8 | skipped |
| 16 | M4 | lead | True | finished | 2021917 | 103 | 28.2 | pass |

**Totals (SDK rows where numeric):** ~47,877,931 tokens; ~1,934 tool calls; ~332.8 agent-minutes across logged runs.

## M4b — human-in-the-loop Power BI Desktop

Store build **2.157.1354.0** on the supervisor laptop. The supervisor opened `bi/powerbi/AravaliAP.pbip` against real `bi.demo` output.

**Correction round 1:** First open showed an **empty** report page—visual definitions lacked layouts/projections—and **no data** because the semantic model used a relative `DataFolder`. Fix: absolute `DataFolder` with trailing backslash and report layout wiring.

**Correction round 2 (after refresh):** Per-field F1 visual failed (`MAX` only accepts a column reference); GST axis was continuous; cards truncated; donut legend showed raw `true`/`false`; `eval_metrics.csv` `run_id` leaked a local temp path. Fixes landed in PBIP/TMDL and export hygiene.

**Result:** All **11** visuals rendered with demo data (50 invoices, **64.00%** auto-allowed, **Rs 167K** grand total, **Rs 47K** unposted, macro F1 **100.0%**). Screenshots under `bi/screenshots/` and MIS workbook checked in Excel.

## M5 release prep

Milestone **M5** (README, changelog, release notes, MIS numeric F1 cell) is prepared on `main` by the lead agent; it does **not** add a row to `runs.jsonl` until the supervisor logs that run separately.

## Contract changes

Proposals under `docs/proposals/`; CI **frozen-files** job fails if frozen paths change without the `contract-change` label.
