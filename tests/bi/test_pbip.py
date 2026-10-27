import json
import re
from pathlib import Path, PureWindowsPath

from bi.export import (
    EVAL_COLUMNS,
    INVOICE_COLUMNS,
    ISSUE_COLUMNS,
    LEDGER_COLUMNS,
    LINE_COLUMNS,
    VENDOR_COLUMNS,
)

PBIP_ROOT = Path(__file__).resolve().parents[2] / "bi" / "powerbi"
DATA_FOLDER_PATH = PureWindowsPath(r"E:\aravali-ap-desk\bi\data")

TABLE_CSV_COLUMNS: dict[str, list[str]] = {
    "Invoices": INVOICE_COLUMNS,
    "LineItems": LINE_COLUMNS,
    "Issues": ISSUE_COLUMNS,
    "Ledger": LEDGER_COLUMNS,
    "Vendors": VENDOR_COLUMNS,
    "EvalMetrics": EVAL_COLUMNS,
}

# Power Query columns not present in exported CSV headers.
COMPUTED_SOURCE_COLUMNS: dict[str, set[str]] = {
    "Invoices": {"Posting Status"},
    "LineItems": {"GST Rate Label"},
}

CHART_VISUAL_TYPES = frozenset({"clusteredBarChart", "clusteredColumnChart", "donutChart"})

BAD_VALUE_DAX = re.compile(r"VALUE\s*\(")
MAX_CALL = re.compile(r"MAX\s*\(")
COLUMN_REF_AFTER_MAX = re.compile(r"\s*(?:[A-Za-z_]\w*|'[^']+')\s*\[")


def _iter_json_files(root: Path):
    yield from root.rglob("*.json")


def _parse_tmdl_measures(text: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"measure\s+'([^']+)'", text)}


def _parse_tmdl_source_columns(text: str) -> set[str]:
    cols: set[str] = set()
    for match in re.finditer(r"sourceColumn:\s*(.+)", text):
        cols.add(match.group(1).strip())
    return cols


def _parse_tmdl_column_types(text: str) -> dict[str, str]:
    types: dict[str, str] = {}
    for match in re.finditer(
        r"column\s+(?:'([^']+)'|(\S+))\s*\n\s*dataType:\s*(\S+)",
        text,
    ):
        name = match.group(1) or match.group(2)
        types[name] = match.group(3)
    return types


MEASURE_BODY_RE = re.compile(r"measure\s+'[^']+'\s*=\s*```\s*\n(.*?)```", re.S)


def _parse_tmdl_measure_bodies(text: str) -> list[str]:
    return [m.group(1) for m in MEASURE_BODY_RE.finditer(text)]


def _collect_query_refs(projections: dict) -> list[str]:
    refs: list[str] = []
    for role in projections.values():
        if not isinstance(role, list):
            continue
        for item in role:
            if isinstance(item, dict) and "queryRef" in item:
                refs.append(item["queryRef"])
    return refs


def _select_names(prototype_query: dict) -> set[str]:
    names: set[str] = set()
    for item in prototype_query.get("Select", []):
        if "Name" in item:
            names.add(item["Name"])
    return names


def test_pbip_json_files_parse() -> None:
    assert PBIP_ROOT.is_dir()
    for path in _iter_json_files(PBIP_ROOT):
        json.loads(path.read_text(encoding="utf-8"))


def test_tmdl_columns_match_export_headers() -> None:
    tables_dir = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables"
    for table, expected_cols in TABLE_CSV_COLUMNS.items():
        tmdl_path = tables_dir / f"{table}.tmdl"
        text = tmdl_path.read_text(encoding="utf-8")
        source_cols = _parse_tmdl_source_columns(text)
        allowed = set(expected_cols) | COMPUTED_SOURCE_COLUMNS.get(table, set())
        for col in source_cols:
            assert col in allowed, f"{table}: unknown sourceColumn {col}"
        assert source_cols, f"{table}: no sourceColumn mappings"


def test_datafolder_absolute_and_partitions_use_csv_quote_style() -> None:
    expr_path = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "expressions.tmdl"
    text = expr_path.read_text(encoding="utf-8")
    match = re.search(r'expression DataFolder = "([^"]+)"', text)
    assert match, "DataFolder expression missing"
    folder = match.group(1)
    assert re.match(r"^[A-Za-z]:\\", folder), "DataFolder must be an absolute Windows path"
    assert folder.endswith("\\"), "DataFolder must end with a backslash"
    assert PureWindowsPath(folder.rstrip("\\")) == DATA_FOLDER_PATH

    tables_dir = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables"
    for path in tables_dir.glob("*.tmdl"):
        body = path.read_text(encoding="utf-8")
        if "partition " not in body:
            continue
        assert "QuoteStyle.Csv" in body, f"{path.name}: partition must use QuoteStyle.Csv"
        assert "QuoteStyle.None" not in body, f"{path.name}: QuoteStyle.None not allowed"


def test_report_visual_configs_have_layouts_and_projections() -> None:
    report_path = PBIP_ROOT / "AravaliAP.Report" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    sections = report.get("sections") or []
    assert sections, "report must have at least one section"
    for section in sections:
        for container in section.get("visualContainers") or []:
            cfg = json.loads(container["config"])
            layouts = cfg.get("layouts") or []
            assert layouts, "visual config missing layouts"
            pos = layouts[0].get("position") or {}
            assert pos.get("width", 0) > 0 and pos.get("height", 0) > 0
            sv = cfg.get("singleVisual") or {}
            if sv.get("visualType") == "textbox":
                continue
            projections = sv.get("projections") or {}
            assert projections, "visual missing projections map"
            pq = sv.get("prototypeQuery") or {}
            select_names = _select_names(pq)
            for qref in _collect_query_refs(projections):
                assert qref in select_names, f"queryRef {qref} missing from prototypeQuery Select"


def test_report_measures_exist_in_model() -> None:
    tables_dir = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables"
    model_measures: set[str] = set()
    for path in tables_dir.glob("*.tmdl"):
        model_measures |= _parse_tmdl_measures(path.read_text(encoding="utf-8"))

    report_path = PBIP_ROOT / "AravaliAP.Report" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    referenced: set[str] = set()
    for section in report.get("sections") or []:
        for container in section.get("visualContainers") or []:
            cfg = json.loads(container["config"])
            sv = cfg.get("singleVisual") or {}
            pq = sv.get("prototypeQuery") or {}
            for item in pq.get("Select", []):
                if "Measure" in item:
                    referenced.add(item["Measure"]["Property"])

    missing = referenced - model_measures
    assert not missing, f"Report references unknown measures: {sorted(missing)}"


def test_tmdl_measures_avoid_value_and_bad_max() -> None:
    tables_dir = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables"
    for path in tables_dir.glob("*.tmdl"):
        for body in _parse_tmdl_measure_bodies(path.read_text(encoding="utf-8")):
            assert not BAD_VALUE_DAX.search(body), f"{path.name}: VALUE() in measure"
            for match in MAX_CALL.finditer(body):
                tail = body[match.end() :]
                assert COLUMN_REF_AFTER_MAX.match(tail), (
                    f"{path.name}: MAX() must reference a column only"
                )


def test_eval_metrics_value_column_is_double() -> None:
    path = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables" / "EvalMetrics.tmdl"
    types = _parse_tmdl_column_types(path.read_text(encoding="utf-8"))
    assert types.get("value") == "double"


def test_chart_category_axes_use_text_columns() -> None:
    tables_dir = PBIP_ROOT / "AravaliAP.SemanticModel" / "definition" / "tables"
    text_columns: dict[str, set[str]] = {}
    for path in tables_dir.glob("*.tmdl"):
        table = path.stem
        types = _parse_tmdl_column_types(path.read_text(encoding="utf-8"))
        text_columns[table] = {name for name, dtype in types.items() if dtype == "string"}

    report_path = PBIP_ROOT / "AravaliAP.Report" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for section in report.get("sections") or []:
        for container in section.get("visualContainers") or []:
            cfg = json.loads(container["config"])
            sv = cfg.get("singleVisual") or {}
            vtype = sv.get("visualType")
            if vtype not in CHART_VISUAL_TYPES:
                continue
            category_refs = (sv.get("projections") or {}).get("Category") or []
            assert category_refs, f"{cfg.get('name')}: chart missing Category"
            for cat in category_refs:
                qref = cat.get("queryRef", "")
                assert "." in qref, f"{cfg.get('name')}: bad category queryRef {qref}"
                table, column = qref.split(".", 1)
                assert column in text_columns.get(table, set()), (
                    f"{cfg.get('name')}: Category {qref} is not a string column"
                )


def test_bi_data_csvs_contain_no_machine_paths() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "bi" / "data"
    drive_path = re.compile(r"[A-Za-z]:\\")
    tmp_token = re.compile(r"tmp", re.I)
    for path in sorted(data_dir.glob("*.csv")):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if drive_path.search(line):
                raise AssertionError(f"{path.name}:{line_no} contains a drive-letter path")
            if tmp_token.search(line):
                raise AssertionError(f"{path.name}:{line_no} contains tmp path token")
