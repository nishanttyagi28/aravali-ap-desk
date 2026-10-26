# Aravali AP Desk — multi-agent rules (M1)

## Roles and path allowlists

Each workstream agent may edit **only** paths under its allowlist (plus create new files there). Paths are relative to the repo root. Enforcement is mechanical via `.cursor/hooks/scope_guard.py` and `.cursor/hooks/ownership.json` (single source of truth).

| Role | Allowlist |
|------|-----------|
| **A** (ingest + extract) | `docai/ingest/`, `docai/extract/`, `tests/ingest/`, `tests/extract/` |
| **B** (validate + API + ledger + db) | `docai/validate/`, `api/`, `ledger/`, `db/`, `tests/validate/`, `tests/api/`, `tests/ledger/`, `tests/db/` |
| **C** (UI) | `ui/` |
| **D** (data + evals + CI + BI + docs) | `datasets/`, `evals/`, `.github/`, `bi/`, `docs/`, `tests/datasets/`, `tests/evals/` |
| **lead** | Entire repo **except** supervisor-only paths |
| **supervisor** | Commits; owns `.vscode/`, `.githooks/`, `.git/` |

### Frozen after M1 (contract change requires lead/supervisor + `contract-change` label)

- `schemas/**`
- `openapi.yaml`
- `pyproject.toml`
- `AGENTS.md`
- `.cursor/**`
- `docai/contracts/**`
- `docai/__init__.py`
- `scripts/**`

Worker roles **A–D** cannot edit frozen or supervisor-only files. **lead** may edit frozen files; **no agent** may edit supervisor-only paths.

### Supervisor-only (never edit in agent worktrees)

- `.vscode/**`
- `.githooks/**`
- `.git/**`

## BBox coordinate convention

Bounding boxes use **PDF user space of the unrotated page**: units are **points**, origin **bottom-left**, **y** increases upward (reportlab / pypdf). Tools that emit top-left coordinates (pdfplumber `top`/`bottom`, OCR pixels) must convert: `y0 = page_height - bottom`, `y1 = page_height - top`.

## M2 extraction entry point (agent A)

```text
docai.extract.extract_file(path: Path, *, mode: str = "offline") -> ExtractedInvoice
```

Callers may pass only a filesystem path; `mode` defaults to offline deterministic extraction.

## Worktree rules

1. **One `.venv` per M2 worktree** — do not share virtualenvs across parallel agent checkouts.
2. **No edits outside your allowlist** — hooks deny with rule IDs `AAD-SCOPE-*` / `AAD-SHELL-*`.
3. **Never `git commit` or `git push`** in worker worktrees (supervisor commits). Hooks block git write commands for A–D; lead may commit locally but not push.
4. **Default extraction mode is `offline`** — CI must pass without API keys.
5. **No secrets in the repo** — use `.env` (gitignored); see `.env.example`.
6. **Tests must pass**: `python -m pytest` from the worktree venv after `pip install -e ".[dev]"`.

## Hook enforcement

- **`preToolUse`** (`Write|Delete|Edit|StrReplace|MultiEdit|NotebookEdit`, `failClosed: true`): resolves the target path, normalises Windows/POSIX paths, denies escapes and out-of-role edits.
- **`beforeShellExecution`** (`failClosed: true`, `--shell`): blocks git writes, destructive deletes, installs outside policy, and writes outside allowlist for A–D.

Unset or unknown `AGENT_ROLE` → **deny everything** (fail closed).

## Requesting a contract change

1. Add a short proposal under `docs/proposals/<topic>.md` (agent D may author; lead reviews), **or**
2. Report the required change in your handoff message with affected models and OpenAPI operations.

CI **frozen-files** job fails if frozen paths change on a PR unless the PR has the `contract-change` label.
