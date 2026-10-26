import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def test_schemas_match_export(tmp_path: Path) -> None:
    committed = {p.name: p.read_text(encoding="utf-8") for p in SCHEMAS.glob("*.json")}
    fresh_dir = tmp_path / "exported"
    subprocess.check_call(
        [sys.executable, str(ROOT / "scripts" / "export_schemas.py"), "--out", str(fresh_dir)],
        cwd=ROOT,
    )
    fresh_names = {p.name for p in fresh_dir.glob("*.json")}
    assert fresh_names == set(committed.keys()), (
        f"schema file set mismatch: extra={fresh_names - set(committed)} "
        f"missing={set(committed) - fresh_names}"
    )
    for name, text in committed.items():
        assert (fresh_dir / name).read_text(encoding="utf-8") == text, f"schema drift: {name}"
