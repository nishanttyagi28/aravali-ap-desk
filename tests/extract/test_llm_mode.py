from pathlib import Path

from docai.contracts.extracted import ExtractedField, FieldSource
from docai.extract import extract, extract_file
from docai.extract.llm import GroqLLMFallback, OllamaLLMFallback
from docai.ingest import load_document

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "datasets" / "sample"


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    def suggest_fields(self, document, missing, partial):
        self.calls += 1
        out: dict[str, ExtractedField] = {}
        for name in missing:
            prior = partial.get(name)
            out[name] = ExtractedField(
                name=name,
                value=prior.value if prior else None,
                raw_text="x",
                bbox=None,
                confidence=0.8,
                source=FieldSource.LLM,
            )
        return out


def test_llm_adapters_import_safe() -> None:
    assert GroqLLMFallback is not None
    assert OllamaLLMFallback is not None


def test_llm_mode_without_adapter_matches_offline() -> None:
    pdf = next(SAMPLE.glob("*.pdf"))
    offline = extract_file(pdf)
    doc = load_document(pdf)
    llm_path = extract(doc, mode="llm", llm=None)
    assert offline.invoice_number == llm_path.invoice_number


def test_fake_llm_adapter_callable() -> None:
    pdf = next(SAMPLE.glob("*.pdf"))
    doc = load_document(pdf)
    adapter = FakeLLM()
    invoice = extract(doc, mode="offline")
    low = [k for k, f in invoice.fields.items() if f.confidence < 0.5]
    adapter.suggest_fields(doc, low or ["invoice_number"], invoice.fields)
    assert adapter.calls == 1
