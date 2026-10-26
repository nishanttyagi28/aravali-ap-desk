from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename


def test_openapi_valid() -> None:
    root = Path(__file__).resolve().parents[2]
    spec_path = root / "openapi.yaml"
    spec, spec_url = read_from_filename(str(spec_path))
    validate(spec, spec_url)
