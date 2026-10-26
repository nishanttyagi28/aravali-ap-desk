from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _assert_lf_only(path: Path) -> None:
    data = path.read_bytes()
    assert b"\r" not in data, f"CR byte found in {path.relative_to(ROOT)}"


def test_committed_text_files_use_lf_line_endings() -> None:
    paths: list[Path] = []
    paths.extend(ROOT.glob("schemas/*.json"))
    paths.extend(ROOT.glob("datasets/sample/*.json"))
    paths.append(ROOT / ".github" / "workflows" / "ci.yml")
    assert paths, "expected at least one file to check"
    for path in sorted(paths):
        _assert_lf_only(path)
