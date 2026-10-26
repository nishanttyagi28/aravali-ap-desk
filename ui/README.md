# AP Desk review UI (M2 — agent C)

React 18 + Vite + TypeScript review console for the AP queue.

## Commands

| Command | Purpose |
|---------|---------|
| `npm run dev:mock` | Dev server with MSW mock (`VITE_MOCK=1`, default API `http://127.0.0.1:8000`) |
| `npm run dev` | Dev server against a real backend |
| `npm run fixtures` | Copy sample PDFs + rebuild `src/mock/data.json` from `../datasets/sample` |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from `../openapi.yaml` |
| `npm test -- --run` | Vitest (unit + component) |
| `npm run build` | Production build |

Set `VITE_API_BASE` in `.env` when the API is not on `http://127.0.0.1:8000`.
