# 0001: A 6M token cap that could not stop a 16.1M run

**Severity:** medium (cost, not correctness)
**Affected:** supervisor harness budget enforcement, M1–M3
**Introduced:** M1  **Found:** M3, 2026-10-26  **Fixed:** mid-run estimator, 2026-10-26
**Existed undetected for:** the whole M1–M2 build

## What we believed

The harness declared a per-run cap of **6M tokens** and a per-run limit of 400
tool calls. The run ledger recorded usage for every run, so cost looked
measured rather than assumed.

## What was true

The cap was evaluated **after** the run finished. Cursor's SDK reports
`totalTokens` once, at run end, so nothing in the harness could observe spend
while the agent was still spending.

Run 11 in the ledger (`docs/multi-agent-build.md`):

| # | step | role | status | total tokens | tool calls | minutes | gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | M3 | lead | **cancelled** | **16,109,745** | 315 | 45.9 | skipped |

16.1M against a 6M cap — **2.7× over**, on a single run. The row says
`cancelled`, but the cancellation happened after the spend, not before it.

So the control was not a limit. It was an assertion, and the assertion failed
after the money was gone.

## How it was found

The run completed and the ledger row was written. The only reason it was noticed
is that somebody read the ledger — the number was 16.1M against a documented cap
of 6M. No alert fired, because no alert existed.

## Why it survived the tests and the gate

The gate checks `ruff` and `pytest`. It has no opinion about spend, and it
should not — the gate runs on code, not on budget.

The deeper reason is a category error in the design: **a budget is a control, and
a control must be able to act before the thing it controls finishes.** The
harness recorded cost accurately and enforced cost not at all. Those were
mistaken for the same thing because the numbers were present in the ledger.

## What changed

A **mid-run estimator** in the supervisor harness cancels a run early:

```
estimated_tokens ≈ 220 × tool_calls²
```

The quadratic fit is deliberate: long agent runs do not grow linearly, because
each step re-sends accumulated context, so cost per step rises with step count.
At the 400 tool-call limit the estimate is far beyond 6M, which means the
estimator, not the nominal cap, is what actually bounds a run.

Effects, both from the ledger:

| # | step | status | tokens | tool calls | note |
| --- | --- | --- | --- | --- | --- |
| 11 | M3 | cancelled after the fact | 16.1M | 315 | the incident |
| 12 | M3 (correction) | finished | 4.01M | 41 | inside the cap |
| 13 | M4 | cancelled mid-run | estimated ~6.06M at 166 calls | 166 | estimator fired |

Run 13 is the fix working: cancellation at 166 tool calls, before the spend,
with the estimate printed at ~6.06M.

## What we did not fix

- **The estimator is a heuristic, not a measurement.** A legitimate run that is
  long in wall-clock but cheap in tokens can be cancelled wrongly. There is no
  way to know after the fact whether that happened, because a cancelled run has
  no SDK usage row.
- **Token accounting double-counts cache reads.** Cursor's `totalTokens` is
  input + output + cache read, and input already includes cache reads. Budgets
  use the sum, so the effective cap is stricter than the number suggests. This
  is documented in the build log rather than corrected.
- **No alerting.** The overrun was found by reading a file.

## What we would do differently

Write the enforcement path before the measurement path. A cap that can only
report is worse than no cap, because it produces confidence without protection.

The same failure shape shows up in [AgentTrust Stack](https://github.com/nishanttyagi28/agenttrust-stack/blob/main/POSTMORTEMS/0001-unsigned-evidence-chain.md):
a check that read the file it was supposed to be checking. Two different
projects, one mistake — verification machinery that observes instead of acts.
