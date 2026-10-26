# Contract change proposals

Contracts (`schemas/**`, `openapi.yaml`, `pyproject.toml`, `AGENTS.md`, `.cursor/**`, `docai/contracts/**`, `scripts/**`) are frozen after M1.

To request a change:

1. Add a short proposal here, e.g. `docs/proposals/<topic>.md`, describing models, API operations, and migration impact.
2. Open a PR with the **`contract-change`** label (or ask the supervisor to apply it after review).
3. Until approved, work around the freeze without breaking existing consumers.

Agent handoffs may also list a **CONTRACT CHANGE REQUEST** in the final report when a freeze blocks required work.
