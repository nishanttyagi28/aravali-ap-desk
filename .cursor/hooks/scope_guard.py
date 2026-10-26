#!/usr/bin/env python3
"""Cursor hook: enforce agent role path and shell allowlists (stdlib only)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

HOOK_DIR = Path(__file__).resolve().parent
OWNERSHIP_PATH = HOOK_DIR / "ownership.json"

PATH_KEYS = ("path", "file_path", "target_file", "filePath")

_GIT_SUBCOMMANDS_WORKER_DENY = frozenset(
    {"commit", "push", "reset", "checkout", "rebase", "clean", "stash"}
)
_GIT_GLOBAL_OPT = r"(?:-C\s+\S+|-c\s+\S+|--(?:git-dir|work-tree|no-pager)(?:=\S+)?|-[A-Za-z]\b)"
_GIT_INVOCATION_RE = re.compile(
    rf"\bgit(?:\.exe)?(?:\s+{_GIT_GLOBAL_OPT})*\s+"
    r"(commit|push|reset|checkout|rebase|clean|stash)\b",
    re.IGNORECASE,
)


def _norm_path_key(path: str) -> str:
    p = path.replace("\\", "/")
    if os.name == "nt":
        return p.lower()
    return p


def _project_root() -> Path:
    env = os.environ.get("CURSOR_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    return cwd


def _load_ownership() -> dict:
    with OWNERSHIP_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _normalize_rel(path_str: str, root: Path) -> str | None:
    if not path_str or not str(path_str).strip():
        return None
    raw = str(path_str).strip().strip('"').strip("'")
    if ".." in PurePosixPath(raw.replace("\\", "/")).parts:
        return None
    p = Path(raw)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(root)
        except ValueError:
            return None
    else:
        rel = (root / p).resolve()
        try:
            rel = rel.relative_to(root)
        except ValueError:
            return None
    parts = rel.parts
    if not parts:
        return ""
    return "/".join(parts)


def _path_matches_prefix(rel: str, prefix: str) -> bool:
    norm_rel = _norm_path_key(rel)
    norm = _norm_path_key(prefix.strip("/"))
    if norm_rel == norm:
        return True
    return norm_rel.startswith(norm + "/") or norm_rel.startswith(norm + "\\")


def _is_supervisor_only(rel: str, prefixes: list[str]) -> bool:
    return any(_path_matches_prefix(rel, pref.replace("\\", "/").strip("/")) for pref in prefixes)


def _is_frozen(rel: str, frozen: list[str]) -> bool:
    for item in frozen:
        norm = item.replace("\\", "/").strip("/")
        if _path_matches_prefix(rel, norm):
            return True
    return False


def _role_allowed(rel: str, role: str, ownership: dict) -> bool:
    prefixes = ownership.get("roles", {}).get(role, [])
    for pref in prefixes:
        norm = pref.replace("\\", "/").strip("/")
        if _path_matches_prefix(rel, norm):
            return True
    return False


def _shell_segments(command: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?:;|&&|\|\||\|)", command) if p.strip()]


def _git_has_denied_subcommand(command: str, *, push_only: bool = False) -> bool:
    deny = frozenset({"push"}) if push_only else _GIT_SUBCOMMANDS_WORKER_DENY
    for segment in _shell_segments(command):
        for match in _GIT_INVOCATION_RE.finditer(segment):
            if match.group(1).lower() in deny:
                return True
    return False


def _deny(rule_id: str, msg: str) -> None:
    payload = {
        "permission": "deny",
        "user_message": f"{rule_id}: {msg}",
        "agent_message": (f"{rule_id}: {msg} Do not retry via shell or another path; report it."),
    }
    print(json.dumps(payload))
    sys.exit(0)


def _allow() -> None:
    print(json.dumps({"permission": "allow"}))
    sys.exit(0)


def _extract_path(tool_input: dict) -> str | None:
    for key in PATH_KEYS:
        val = tool_input.get(key)
        if val:
            return str(val)
    return None


def check_file_access(hook_input: dict) -> None:
    root = _project_root()
    ownership = _load_ownership()
    tool_input = hook_input.get("tool_input") or {}
    raw_path = _extract_path(tool_input)
    if raw_path is None:
        _deny("AAD-SCOPE-000", "missing or invalid target path in tool_input")

    rel = _normalize_rel(raw_path, root)
    if rel is None:
        _deny("AAD-SCOPE-005", "path outside workspace or invalid escape")

    role = os.environ.get("AGENT_ROLE", "").strip()
    if not role:
        _deny("AAD-SCOPE-001", "AGENT_ROLE is not set")

    supervisor = ownership.get("supervisor_only", [])
    frozen = ownership.get("frozen", [])

    if _is_supervisor_only(rel, supervisor):
        if role == "lead":
            _deny("AAD-SCOPE-004", "supervisor-only path")
        _deny("AAD-SCOPE-004", "supervisor-only path")

    if role == "lead":
        _allow()

    if _is_frozen(rel, frozen):
        _deny("AAD-SCOPE-003", "frozen contract or shared file")

    if role in ownership.get("roles", {}):
        if _role_allowed(rel, role, ownership):
            _allow()
        _deny("AAD-SCOPE-002", f"role {role} may not modify this path")

    _deny("AAD-SCOPE-001", f"unknown role '{role}'")


_EDITABLE_PIP_RE = re.compile(
    r"(?:^|[\s\"'])(?:\.venv[\\/]Scripts[\\/]python|\.venv/bin/python|python)\s+-m\s+pip\s+install\s+-e\s+",
    re.IGNORECASE,
)

_RM_DENY_RE = re.compile(
    r"\brm\s+-rf\b|Remove-Item\s+.*-Recurse",
    re.IGNORECASE,
)

_PIP_INSTALL_RE = re.compile(r"\bpip\s+install\b", re.IGNORECASE)
_NPM_INSTALL_RE = re.compile(r"\bnpm\s+(install|ci)\b", re.IGNORECASE)
_NPX_RE = re.compile(r"\bnpx\b", re.IGNORECASE)

_SHELL_WRITE_TOOLS = re.compile(
    r"(?:>>?|Set-Content|Out-File|\btee\b|sed\s+-i|\bmv\b|\bcp\b|Move-Item|Copy-Item)",
    re.IGNORECASE,
)


def _token_in_allowlist(token: str, role: str, ownership: dict) -> bool:
    prefixes = ownership.get("roles", {}).get(role, [])
    norm = _norm_path_key(token.strip().strip('"').strip("'").lstrip("./"))
    if not norm or norm in (".", ".."):
        return True
    for pref in prefixes:
        p = _norm_path_key(pref.strip("/"))
        if norm == p or norm.startswith(p + "/"):
            return True
    return False


def _shell_targets_outside_allowlist(command: str, role: str, ownership: dict) -> bool:
    """Return True when a shell redirection or copy/move target is outside the role allowlist."""
    if role == "lead":
        return False
    patterns = (
        r"(?:>>?)\s*([^\s|;&]+)",
        r"Set-Content\s+-Path\s+([^\s]+)",
        r"(?:\|\s*)?Out-File\s+([^\s]+)",
        r"Move-Item\s+[^\s]+\s+([^\s]+)",
        r"Copy-Item\s+[^\s]+\s+([^\s]+)",
        r"\bcp\s+[^\s]+\s+([^\s]+)",
        r"\bmv\s+[^\s]+\s+([^\s]+)",
        r"\btee\s+([^\s|;&]+)",
        r"sed\s+-i\s+\S+\s+([^\s|;&]+)",
    )
    for pat in patterns:
        for m in re.finditer(pat, command, re.IGNORECASE):
            if not _token_in_allowlist(m.group(1), role, ownership):
                return True
    return False


def _npx_allowed_for_c(command: str, cwd: str) -> bool:
    cwd_norm = cwd.replace("\\", "/")
    if not cwd_norm.rstrip("/").endswith("ui"):
        return False
    lower = command.lower()
    if "openapi-typescript" in lower:
        return True
    return bool(re.search(r"npx\s+msw\s+init\s+public\s+--save", command, re.IGNORECASE))


def check_shell(command: str, cwd: str | None) -> None:
    ownership = _load_ownership()
    role = os.environ.get("AGENT_ROLE", "").strip()
    cmd = command.strip()
    work_cwd = (cwd or os.getcwd()).replace("\\", "/")

    if role == "lead":
        if _git_has_denied_subcommand(cmd, push_only=True):
            _deny("AAD-SHELL-003", "lead may not git push")
        _allow()

    if not role or role not in ownership.get("roles", {}):
        _deny("AAD-SCOPE-001", "AGENT_ROLE missing or unknown for shell")

    if _git_has_denied_subcommand(cmd):
        _deny("AAD-SHELL-001", "git write operations are blocked for worker roles")

    if _RM_DENY_RE.search(cmd):
        _deny("AAD-SHELL-001", "recursive delete is blocked")

    if _SHELL_WRITE_TOOLS.search(cmd) and _shell_targets_outside_allowlist(cmd, role, ownership):
        _deny("AAD-SHELL-001", "shell write/copy outside role allowlist")

    if _EDITABLE_PIP_RE.search(cmd):
        _allow()

    if _PIP_INSTALL_RE.search(cmd) and not _EDITABLE_PIP_RE.search(cmd):
        _deny("AAD-SHELL-002", "only editable install of this project into .venv is allowed")

    if _NPM_INSTALL_RE.search(cmd):
        if role == "C" and work_cwd.rstrip("/").endswith("ui"):
            _allow()
        _deny("AAD-SHELL-002", "npm install/ci only allowed for role C inside ui/")

    if _NPX_RE.search(cmd):
        if role == "C" and _npx_allowed_for_c(cmd, work_cwd):
            _allow()
        _deny("AAD-SHELL-002", "npx restricted for this role")

    _allow()


def main() -> None:
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        _deny("AAD-SCOPE-000", "invalid JSON on stdin")

    if "--shell" in sys.argv:
        command = hook_input.get("command") or hook_input.get("cmd") or ""
        cwd = hook_input.get("cwd")
        check_shell(str(command), str(cwd) if cwd else None)
    else:
        check_file_access(hook_input)


if __name__ == "__main__":
    main()
