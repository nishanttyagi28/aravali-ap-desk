from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"


class _RejectDuplicateKeysLoader(yaml.SafeLoader):
    pass


def _mapping_constructor(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False):
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate mapping key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_RejectDuplicateKeysLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _mapping_constructor,
)


def test_ci_workflow_yaml_no_duplicate_keys() -> None:
    text = CI_PATH.read_text(encoding="utf-8")
    doc = yaml.load(text, Loader=_RejectDuplicateKeysLoader)
    assert "jobs" in doc
    assert "test" in doc["jobs"]
    assert "frozen-files" in doc["jobs"]

    test_job = doc["jobs"]["test"]
    runs = "\n".join(step.get("run", "") for step in test_job["steps"] if isinstance(step, dict))
    assert "ruff check ." in runs
    assert "ruff format --check ." in runs
    assert "pytest -q" in runs
    assert "datasets.synth" in runs
    assert "export_schemas.py" in runs
    assert "git diff --exit-code schemas/" in runs

    frozen_steps = doc["jobs"]["frozen-files"]["steps"]
    check_step = next(s for s in frozen_steps if s.get("name") == "Check frozen paths")
    env = check_step["env"]
    assert set(env.keys()) == {"BASE", "HEAD", "PR_LABELS"}
