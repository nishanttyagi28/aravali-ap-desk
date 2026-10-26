"""Seal providers for tamper-evident ledger manifests."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from docai.contracts.ledger import SealProvider as SealProviderKind
from docai.contracts.ledger import SealRef, WitnessStatus


class SealProvider(Protocol):
    def seal_receipt(self, receipt_sha256: str) -> SealRef: ...

    def witness(self, entry_hash: str, manifest_sha256: str, chain_prev: str | None) -> str:
        """Return ``match`` or ``mismatch`` (legacy chain on entry_hash)."""
        ...


def canonical_manifest_json(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)


def manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = canonical_manifest_json(manifest).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StubSealProvider:
    def seal_receipt(self, receipt_sha256: str) -> SealRef:
        return SealRef(
            provider=SealProviderKind.STUB,
            commit_id=receipt_sha256,
            manifest_sha256=receipt_sha256,
            witness_status=WitnessStatus.LOCAL,
        )

    def witness(self, entry_hash: str, manifest_sha256: str, chain_prev: str | None) -> str:
        material = f"{chain_prev or ''}|{manifest_sha256}"
        expected = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return "match" if expected == entry_hash else "mismatch"


class KarmaSakshiNotAvailable(Exception):
    """Raised when the optional karmasakshi package is not installed."""


def karma_sakshi_provider() -> SealProvider:
    try:
        import karmasakshi  # noqa: F401
    except ImportError as exc:
        raise KarmaSakshiNotAvailable("karmasakshi is not installed") from exc
    raise KarmaSakshiNotAvailable("karmasakshi adapter not configured")
