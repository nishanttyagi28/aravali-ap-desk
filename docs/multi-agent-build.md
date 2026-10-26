# Multi-agent build (M2)

## Roles and allowlists

See `AGENTS.md` for role **A–D**, **lead**, and **supervisor** path allowlists. Enforcement is mechanical:

- **Repo hooks** (`.cursor/hooks/scope_guard.py`, `ownership.json`): `preToolUse` and `beforeShellExecution` deny out-of-scope edits and git writes for worker roles.
- **Supervisor scope check** (`check-scope.ts <role> [--staged]`): git-diff ownership check against the supervisor copy of allowlists; runs after every agent run and as the git pre-commit hook (independent of repo hooks).

Unset or unknown `AGENT_ROLE` → deny everything (fail closed).

## Runner harness (`run-agent.ts`)

- Refuses to start when today's tokens ≥ **40M** (`perDayMaxTokens`).
- Cancels a run above **6M** tokens, **400** tool calls, or **60** minutes.
- Exports **`AGENT_ROLE`** for scope guard.
- Max **2** correction rounds per step.

## Gate (`gate.ts`)

Runs in the worktree venv: `ruff check .`, `ruff format --check .`, `pytest -q`. Exit 0 only if all pass.

## Run log (`logs/runs.jsonl`)

Each line records agentId, runId, model, prompt hash, tokens, duration, files touched, gate result, plus approval/refusal events.

## Approval (`approve-and-push.ts`)

Manual by default (human types `approve`). M1/M2 milestones are pre-approved as **auto** with the note logged instead. Refuses on scope/gate failure. Supervisor commits with a `Supervisor-Approval:` trailer. **Agents never commit.**

## Worktrees

One `.venv` per M2 worktree; do not share virtualenvs across parallel agent checkouts. Supervisor gate uses that worktree's venv, not the main repo's.

## Contract changes

Frozen paths require lead/supervisor + `contract-change` label on PRs. Proposals go under `docs/proposals/` (see [proposals/README.md](proposals/README.md)).
