"""Table-driven tests for .cursor/hooks/scope_guard.py (real subprocess)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".cursor" / "hooks" / "scope_guard.py"
UI_CWD = str(ROOT / "ui")

FROZEN_PATHS = [
    "schemas/X.schema.json",
    "openapi.yaml",
    "pyproject.toml",
    "AGENTS.md",
    ".cursor/hooks/ownership.json",
    "docai/contracts/x.py",
    "docai/__init__.py",
    "scripts/x.py",
]


def _run_hook(
    stdin: dict,
    *,
    role: str | None = "A",
    shell: bool = False,
) -> dict:
    env = os.environ.copy()
    env["CURSOR_PROJECT_DIR"] = str(ROOT)
    if role is None:
        env.pop("AGENT_ROLE", None)
    else:
        env["AGENT_ROLE"] = role
    cmd = [sys.executable, str(SCRIPT)]
    if shell:
        cmd.append("--shell")
    proc = subprocess.run(
        cmd,
        input=json.dumps(stdin),
        text=True,
        capture_output=True,
        env=env,
        cwd=ROOT,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return json.loads(proc.stdout.strip())


def _path_tool(path: str, key: str = "path") -> dict:
    return {"tool_input": {key: path}}


def _shell_body(command: str, cwd: str | None = None) -> dict:
    body: dict = {"command": command}
    if cwd is not None:
        body["cwd"] = cwd
    return body


# --- path allow ---
_PATH_ALLOW = [
    ("A-ingest", "A", _path_tool("docai/ingest/x.py"), "allow", None),
    ("A-extract", "A", _path_tool("docai/extract/x.py"), "allow", None),
    ("B-api", "B", _path_tool("api/x.py"), "allow", None),
    ("B-ledger", "B", _path_tool("ledger/x.py"), "allow", None),
    ("B-db", "B", _path_tool("db/x.py"), "allow", None),
    ("B-validate", "B", _path_tool("docai/validate/x.py"), "allow", None),
    ("C-ui", "C", _path_tool("ui/src/App.tsx"), "allow", None),
    ("D-datasets", "D", _path_tool("datasets/foo.py"), "allow", None),
    ("D-evals", "D", _path_tool("evals/run.py"), "allow", None),
    ("D-github", "D", _path_tool(".github/workflows/ci.yml"), "allow", None),
    ("D-bi", "D", _path_tool("bi/README.md"), "allow", None),
    ("D-docs", "D", _path_tool("docs/metrics.md"), "allow", None),
    ("lead-contracts", "lead", _path_tool("docai/contracts/x.py"), "allow", None),
]

# --- OUT_OF_ROLE ---
_PATH_OUT_OF_ROLE = [
    ("C-extract", "C", _path_tool("docai/extract/x.py"), "deny", "AAD-SCOPE-002"),
    (
        "C-ingest-abs",
        "C",
        _path_tool(str(ROOT / "docai" / "ingest" / "x.py"), "file_path"),
        "deny",
        "AAD-SCOPE-002",
    ),
    ("A-api", "A", _path_tool("api/x.py"), "deny", "AAD-SCOPE-002"),
    ("B-ui", "B", _path_tool("ui/x.ts"), "deny", "AAD-SCOPE-002"),
    ("D-ingest", "D", _path_tool("docai/ingest/x.py"), "deny", "AAD-SCOPE-002"),
]

# --- FROZEN (all roles × all frozen paths) ---
_PATH_FROZEN = [
    (
        f"frozen-{role}-{path.replace('/', '_')}",
        role,
        _path_tool(path),
        "deny",
        "AAD-SCOPE-003",
    )
    for role in ("A", "B", "C", "D")
    for path in FROZEN_PATHS
]

# --- SUPERVISOR_ONLY ---
_PATH_SUPERVISOR = [
    ("lead-vscode", "lead", _path_tool(".vscode/tasks.json"), "deny", "AAD-SCOPE-004"),
    ("lead-githooks", "lead", _path_tool(".githooks/pre-commit"), "deny", "AAD-SCOPE-004"),
]

# --- NO_ROLE ---
_PATH_NO_ROLE = [
    ("no-role-unset", None, _path_tool("docai/ingest/x.py"), "deny", "AAD-SCOPE-001"),
    ("unknown-role", "Z", _path_tool("docai/ingest/x.py"), "deny", "AAD-SCOPE-001"),
]

# --- OUTSIDE_WORKSPACE ---
_PATH_OUTSIDE = [
    ("parent-escape", "A", _path_tool("../outside.py"), "deny", "AAD-SCOPE-005"),
    ("dotdot-escape", "A", _path_tool("docai/ingest/../../x.py"), "deny", "AAD-SCOPE-005"),
    ("abs-outside", "A", _path_tool("C:/Windows/not-in-workspace.py"), "deny", "AAD-SCOPE-005"),
]

# --- INVALID_INPUT + path keys ---
_PATH_INVALID_AND_KEYS = [
    ("missing-path", "A", {"tool_input": {}}, "deny", "AAD-SCOPE-000"),
]
for _key in ("path", "file_path", "target_file", "filePath"):
    _PATH_INVALID_AND_KEYS.append(
        (f"key-{_key}", "A", _path_tool("docai/ingest/x.py", _key), "allow", None),
    )

if sys.platform == "win32":
    _PATH_FROZEN.append(
        (
            "frozen-A-case-windows",
            "A",
            _path_tool("DOCAI/Contracts/x.py"),
            "deny",
            "AAD-SCOPE-003",
        )
    )

_PATH_CASES = (
    _PATH_ALLOW
    + _PATH_OUT_OF_ROLE
    + _PATH_FROZEN
    + _PATH_SUPERVISOR
    + _PATH_NO_ROLE
    + _PATH_OUTSIDE
    + _PATH_INVALID_AND_KEYS
)


def test_scope_guard_invalid_json_stdin() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="{not-json",
        text=True,
        capture_output=True,
        env={**os.environ, "CURSOR_PROJECT_DIR": str(ROOT), "AGENT_ROLE": "A"},
        cwd=ROOT,
    )
    out = json.loads(proc.stdout.strip())
    assert out["permission"] == "deny"
    assert "AAD-SCOPE-000" in out["user_message"]


@pytest.mark.parametrize(
    ("case_id", "role", "stdin", "expected", "rule_id"),
    _PATH_CASES,
)
def test_scope_guard_path(
    case_id: str, role: str | None, stdin: dict, expected: str, rule_id: str | None
):
    out = _run_hook(stdin, role=role, shell=False)
    assert out["permission"] == expected, (case_id, out)
    if rule_id:
        assert rule_id in out["user_message"], out["user_message"]


_SHELL_DENY_001_A = [
    ("git-commit", "git commit -m x"),
    ("git-C-commit", "git -C . commit -m x"),
    ("git-c-push", "git -c user.name=x push"),
    ("cd-git-stash", "cd docai; git stash"),
    ("rm-rf", "rm -rf docai/ingest"),
    ("remove-item", "Remove-Item -Recurse docai/ingest"),
    ("redirect-api", "echo x > api/x.py"),
    ("set-content", "Set-Content -Path ledger/x.py -Value 1"),
    ("out-file", "echo x | Out-File docai/contracts/x.py"),
    ("tee", "echo x | tee api/x.py"),
    ("sed-i", "sed -i s/a/b/ api/x.py"),
    ("cp", "cp docai/ingest/a.py api/a.py"),
    ("move-item", "Move-Item docai/ingest/a.py api/a.py"),
]

_SHELL_CASES: list[tuple[str, str | None, dict, str, str | None]] = []

for _id, _cmd in _SHELL_DENY_001_A:
    _SHELL_CASES.append((f"shell-001-{_id}", "A", _shell_body(_cmd), "deny", "AAD-SHELL-001"))

_SHELL_CASES.append(
    ("shell-001-allow-ingest", "A", _shell_body("echo x > docai/ingest/x.txt"), "allow", None)
)

_SHELL_CASES.extend(
    [
        ("shell-002-pip", "A", _shell_body("pip install requests"), "deny", "AAD-SHELL-002"),
        ("shell-002-npm-i", "A", _shell_body("npm install"), "deny", "AAD-SHELL-002"),
        ("shell-002-npm-ci", "A", _shell_body("npm ci"), "deny", "AAD-SHELL-002"),
        (
            "shell-002-npx-msw-A",
            "A",
            _shell_body("npx msw init public --save"),
            "deny",
            "AAD-SHELL-002",
        ),
        (
            "shell-002-npm-ci-C-root",
            "C",
            _shell_body("npm ci", cwd=str(ROOT)),
            "deny",
            "AAD-SHELL-002",
        ),
        ("shell-002-npm-i-C-ui", "C", _shell_body("npm install", cwd=UI_CWD), "allow", None),
        ("shell-002-npm-ci-C-ui", "C", _shell_body("npm ci", cwd=UI_CWD), "allow", None),
        (
            "shell-002-npx-msw-C-ui",
            "C",
            _shell_body("npx msw init public --save", cwd=UI_CWD),
            "allow",
            None,
        ),
        (
            "shell-002-npx-oapi-C-ui",
            "C",
            _shell_body(
                "npx openapi-typescript ../openapi.yaml -o src/api/schema.d.ts",
                cwd=UI_CWD,
            ),
            "allow",
            None,
        ),
        (
            "shell-002-pip-editable",
            "A",
            _shell_body("python -m pip install -e .[dev]"),
            "allow",
            None,
        ),
        (
            "shell-002-pip-editable-quoted",
            "A",
            _shell_body('python -m pip install -e ".[dev,ocr]"'),
            "allow",
            None,
        ),
        (
            "shell-002-venv-win",
            "A",
            _shell_body(r'.venv\Scripts\python -m pip install -e ".[dev]"'),
            "allow",
            None,
        ),
        (
            "shell-002-venv-unix",
            "A",
            _shell_body('.venv/bin/python -m pip install -e ".[dev]"'),
            "allow",
            None,
        ),
        ("shell-npm-run-all", "A", _shell_body("npm run lint"), "allow", None),
        ("shell-pytest-all", "A", _shell_body("python -m pytest -q"), "allow", None),
        ("shell-ruff-all", "A", _shell_body("ruff check ."), "allow", None),
        ("shell-003-push", "lead", _shell_body("git push origin main"), "deny", "AAD-SHELL-003"),
        ("shell-003-push-C", "lead", _shell_body("git -C . push"), "deny", "AAD-SHELL-003"),
        ("shell-003-status", "lead", _shell_body("git status"), "allow", None),
        ("shell-003-commit", "lead", _shell_body("git commit -m x"), "allow", None),
        ("shell-003-pip", "lead", _shell_body("pip install requests"), "allow", None),
    ]
)


@pytest.mark.parametrize(
    ("case_id", "role", "stdin", "expected", "rule_id"),
    _SHELL_CASES,
)
def test_scope_guard_shell(
    case_id: str,
    role: str | None,
    stdin: dict,
    expected: str,
    rule_id: str | None,
):
    out = _run_hook(stdin, role=role, shell=True)
    assert out["permission"] == expected, (case_id, out)
    if rule_id:
        assert rule_id in out["user_message"], out["user_message"]
