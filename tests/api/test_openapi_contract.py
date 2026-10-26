from pathlib import Path

import yaml

from api.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def test_paths_methods_and_status_codes_match_openapi() -> None:
    spec = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
    app = create_app()
    generated = app.openapi()
    for path, operations in spec["paths"].items():
        assert path in generated["paths"], f"missing path {path}"
        for method, operation in operations.items():
            assert method in generated["paths"][path], f"missing {method.upper()} {path}"
            spec_codes = {int(code) for code in operation.get("responses", {})}
            app_codes = {
                int(code) for code in generated["paths"][path][method].get("responses", {})
            }
            assert spec_codes <= app_codes, f"{path} {method} missing {spec_codes - app_codes}"
