"""Optional LLM fallback for low-confidence fields."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

from docai.contracts.extracted import ExtractedField
from docai.ingest.models import Document


@runtime_checkable
class LLMFallback(Protocol):
    """Fill or refine fields that offline rules could not locate confidently."""

    def suggest_fields(
        self,
        document: Document,
        missing: list[str],
        partial: dict[str, ExtractedField],
    ) -> dict[str, ExtractedField]:
        """Return suggested fields for the given names only."""
        ...


class GroqLLMFallback:
    """Groq chat completion adapter (requires GROQ_API_KEY and groq package)."""

    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        self.model = model

    def suggest_fields(
        self,
        document: Document,
        missing: list[str],
        partial: dict[str, ExtractedField],
    ) -> dict[str, ExtractedField]:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        from groq import Groq

        client = Groq(api_key=api_key)
        text = " ".join(w.text for w in document.words[:500])
        prompt = f"Extract JSON for fields {missing} from invoice text:\n{text[:8000]}"
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        return _parse_llm_json(content, missing)


class OllamaLLMFallback:
    """Ollama HTTP adapter (OLLAMA_HOST, default http://localhost:11434)."""

    def __init__(self, model: str = "llama3.2") -> None:
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    def suggest_fields(
        self,
        document: Document,
        missing: list[str],
        partial: dict[str, ExtractedField],
    ) -> dict[str, ExtractedField]:
        import httpx

        text = " ".join(w.text for w in document.words[:500])
        prompt = f"Extract JSON for fields {missing} from invoice text:\n{text[:8000]}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.host}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            content = resp.json().get("response", "{}")
        return _parse_llm_json(content, missing)


def _parse_llm_json(content: str, names: list[str]) -> dict[str, ExtractedField]:
    import json
    import re

    from docai.contracts.extracted import FieldSource

    match = re.search(r"\{.*\}", content, re.DOTALL)
    data: dict[str, Any] = json.loads(match.group(0) if match else "{}")
    out: dict[str, ExtractedField] = {}
    for name in names:
        if name not in data:
            continue
        val = data[name]
        out[name] = ExtractedField(
            name=name,
            value=val,
            raw_text=str(val),
            bbox=None,
            confidence=0.6,
            source=FieldSource.LLM,
        )
    return out
