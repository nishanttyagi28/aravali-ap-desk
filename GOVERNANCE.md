# How this repo is built: a human supervisor, agents in cages

Aravali AP Desk v0.1.0 was built by a **human-controlled supervisor** driving
Cursor agents inside scoped worktrees. The supervisor does not write product
code. It sets `AGENT_ROLE`, runs one agent per workstream, enforces budgets,
runs an independent scope check, runs the quality gate, and commits.

This file is the front door to that machinery. The full build log — including
the token ledger and the merges — is [docs/multi-agent-build.md](docs/multi-agent-build.md).

The reason to read any of this: an AP desk decides whether a ₹4,00,000 invoice is
paid. "An AI wrote it" is not a disqualifier, but "nobody could say what the AI
was allowed to touch" is.

## 1. Ownership is a file, not a convention

`.cursor/hooks/ownership.json` is the single source of truth, in three tiers:

| Tier | Contents | Who may write |
| --- | --- | --- |
| `supervisor_only` | `.vscode/`, `.githooks/`, `.git/` | supervisor, by hand, never an agent |
| `frozen` | `schemas/**`, `openapi.yaml`, `pyproject.toml`, `AGENTS.md`, `.cursor/**`, `docai/contracts/**`, `scripts/**` | lead/supervisor only, and a contract change needs the `contract-change` label |
| `roles.A–D` | ingest+extract · validate+API+ledger+DB · UI · data+evals+CI+BI+docs | that role only |

A worker cannot edit the frozen contracts it is coded against. The UI agent
cannot reach into the ledger. That separation is the point: **an agent that can
change both the thing and the test of the thing has not been verified, it has
been trusted.**

## 2. The hooks fail closed

`.cursor/hooks/scope_guard.py` runs on `preToolUse` (Write/Edit/StrReplace/
Delete/NotebookEdit) and `beforeShellExecution`. It denies with rule IDs the
agent can actually read:

- `AAD-SCOPE-000` — missing or invalid target path
- `AAD-SCOPE-001` — `AGENT_ROLE` unset → **deny everything**
- `AAD-SCOPE-003` — frozen contract edited by a worker
- `AAD-SCOPE-004` — supervisor-only path
- `AAD-SCOPE-005` — path escape outside the workspace
- `AAD-SHELL-001…003` — git writes, destructive commands, out-of-scope installs

`AGENT_ROLE` unset means deny, not allow. A guard that fails open is decoration.

## 3. Agents never commit

Workers cannot run `git commit`, `push`, `reset`, `checkout`, `rebase`, `clean`
or `stash` — `_GIT_SUBCOMMANDS_WORKER_DENY` in `scope_guard.py`. The supervisor
commits, and a second independent check (`check-scope.ts <role> --staged`) runs
against the staged diff before the commit exists, because the hook's path
normalization and the git diff's disagree on Windows.

That second check is not redundancy for its own sake. It exists because the hook
was bypassed once: `git -C . commit` got through a rule that only matched bare
`git commit`. The fix was to match the git *write verb* rather than the literal
command string.

## 4. Every commit records its approval

19 of 24 commits carry a trailer:

```
Supervisor-Approval: auto: pre-approved by user 2026-10-26
                     (M3-M5 relayed 10:06 PM IST);
                     M6 (viewer bug fix) approved by owner 2026-10-27 9:49 PM IST
```

**Be honest about what that means.** All 19 are `auto:` — approval was *relayed*
under a standing policy, not granted interactively per commit. Only one carries
an explicit owner sign-off, and that one is the viewer bug fix in
[postmortem 0002](POSTMORTEMS/0002-viewer-render-race.md).

The trailer is a provenance record, not a rubber stamp. It says which of the two
happened, and the ratio is the number to watch.

## 5. Budgets are enforced mid-run

Per-run caps: 6M tokens, 400 tool calls, 60 minutes. These were **not** enforced
at first — the SDK reports `totalTokens` only at run end, so one run reached
16.1M tokens against a 6M cap before anyone could stop it. A mid-run estimator
now cancels early. Full account:
[postmortem 0001](POSTMORTEMS/0001-token-cap-overrun.md).

The per-run ledger (`logs/runs.jsonl`, reproduced in
`docs/multi-agent-build.md`) records agent, model, prompt hash, token
breakdown, duration, files touched, and gate result for every run.

## 6. The gate is what decides, not the agent

After each run, in that worktree's own venv:

```
ruff check .
ruff format --check .
python -m pytest -q
```

Approve-and-push refuses on scope or gate failure, and merges to `main` use
`git merge --no-ff` with the gate re-run on merged main and a rollback on
failure. A green agent run is a proposal; the gate and the supervisor are the
decision.

## 7. Failures get written down

`POSTMORTEMS/` records what broke, how it was found, and what changed. Two
entries, both from the real build log:

| # | What broke |
| --- | --- |
| [0001](POSTMORTEMS/0001-token-cap-overrun.md) | A 6M token cap that could not stop a 16.1M run |
| [0002](POSTMORTEMS/0002-viewer-render-race.md) | Review UI rendered pages upside down with misaligned bbox overlays |

## What this does not do

- **The lane map is a human judgment.** Nothing verifies that role C *should*
  own all of `ui/`. That call is in `AGENTS.md` and it can be wrong.
- **Approval is mostly relayed.** 19 of 24 commits were auto-approved under a
  standing owner policy. That is a real reduction in per-change scrutiny.
- **Lanes constrain paths, not quality.** An agent inside its lane can write bad
  code. Tests and the gate are the only defence against that, and they only
  catch what someone thought to assert — see postmortem 0002.
- **The hook is intimate with Cursor.** Porting to another runner means porting
  `scope_guard.py`, not just pointing it at a different model.
- **Coordinates this document does not make safe.** A misaligned overlay on a
  BLOCK invoice means a human approves while looking at the wrong part of the
  page. That happened. It is why 0002 exists.
