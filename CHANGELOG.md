# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-27

### Added

#### M1 — Contracts and harness

- Pydantic contracts (`docai/contracts/`), JSON Schema export, OpenAPI stub, and synthetic dataset layout.
- Multi-agent path allowlists (`AGENTS.md`, `.cursor/hooks/ownership.json`) with fail-closed Cursor hooks (`AAD-SCOPE-*`, `AAD-SHELL-*`).
- CI workflow: ruff, pytest, frozen-files guard, schema/OpenAPI validation.
- Invoice PDF generator and sample datasets.

#### M2 — Pipeline (parallel agents A–D)

- **Ingest + extract (A):** `load_document`, offline deterministic extraction (`docai.extract.extract_file`), optional OCR/LLM paths, bbox provenance in PDF user space.
- **Validate + API + ledger + DB (B):** GST validation engine, decision policy, FastAPI upload/review/post, SQLite persistence, hash-chained ledger stub receipts.
- **Review UI (C):** Vite/React review queue, invoice detail with PDF bbox overlay, MSW fixtures for local dev.
- **Evals + CI (D):** `evals.run` / `evals.gate`, AgentEval bridge, `offline-v1` baseline and `thresholds.yaml`, blocking eval jobs in GitHub Actions.

#### M3 — Integration

- End-to-end wiring: dev scripts (`scripts/dev.ps1`, `make dev`), idempotent DB seed from `datasets/sample`, merged decision policy and review flows on main.

#### M4 — Seal, BI, and MIS

- Sealed ledger verify CLI (`ledger.verify`), `SealRef` on post responses.
- BI CSV marts (`bi.export`), deterministic `bi.demo`, Excel MIS (`bi.mis`), Power BI PBIP project (`bi/powerbi/AravaliAP.pbip`).
- Human-verified Power BI Desktop refresh path and screenshot capture under `bi/screenshots/`.

### Known limitations

- Ledger sealing is a **local stub** (`provider: stub`, `witness_status: local`), not a production witness network.
- Default extraction is **offline**; LLM mode requires API keys and is not used in CI gates.
- Power BI requires Desktop with PBIP preview and a machine-local `DataFolder` parameter (trailing backslash on Windows).
- OCR/scanned PDF quality varies; eval OCR job is report-only at partial scanned ratio.
- Review UI screenshots for queue and invoice-detail bbox overlay are not yet checked into the repo.
- Decision accuracy on the offline v1 baseline is **0.90**, not 1.00 (by design of synthetic truth vs engine).

[0.1.0]: https://github.com/aravali-ap-desk/aravali-ap-desk/releases/tag/v0.1.0
