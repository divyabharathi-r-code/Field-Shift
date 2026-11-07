# FieldShift

**NASA Space Apps Challenge 2026 — "Field Shift: Adapting Farms with NASA Data"**

A transparent decision-support and scenario-exploration tool that combines NASA Earth-observation
data, local soil information, crop characteristics, and farmer priorities to explore **resilient
crop-rotation strategies**.

> The question is not *"what crop should the farmer plant?"*
> It is **"which crop rotation remains more resilient when environmental conditions and farmer
> priorities change?"**

FieldShift therefore ranks *rotations*, scores them across multiple dimensions, and then stress-tests
those rankings against simulated environmental shifts and shifting farmer priorities — showing which
strategy stays robust and which one is fragile.

---

## Status

**Phase 0 — planning only.** No application code has been written yet. This repository currently
contains the architecture, contracts, and milestone plan. Implementation starts after the plan is approved.

| Phase | Area | State |
|---|---|---|
| 0 | Project rules + architecture | ✅ documented (below) |
| 1–13 | Repository → Submission | ⏳ awaiting plan approval |

## Plan documents (read in order)

1. [`docs/00_PROJECT_RULES.md`](docs/00_PROJECT_RULES.md) — concept, non-negotiable architectural rules, the four data classes, scope guard
2. [`docs/01_ARCHITECTURE_AND_FOLDERS.md`](docs/01_ARCHITECTURE_AND_FOLDERS.md) — layered architecture, proposed folder tree, key decisions & tech choices
3. [`docs/02_MODULE_RESPONSIBILITIES.md`](docs/02_MODULE_RESPONSIBILITIES.md) — per-module does / does-NOT / inputs→outputs / tests
4. [`docs/03_API_CONTRACT.md`](docs/03_API_CONTRACT.md) — endpoints, request/response schemas, envelopes, contract tests
5. [`docs/04_DATA_FLOW.md`](docs/04_DATA_FLOW.md) — end-to-end pipeline, data class per hop, caching/determinism, degradation paths
6. [`docs/05_DATA_SOURCES_AND_PROVENANCE.md`](docs/05_DATA_SOURCES_AND_PROVENANCE.md) — registry schema + candidate sources (**unverified**, must be verified before use)
7. [`docs/06_MODEL_ASSUMPTIONS.md`](docs/06_MODEL_ASSUMPTIONS.md) — assumption register, scoring-dimension definitions, deliberate simplifications
8. [`docs/07_MILESTONES.md`](docs/07_MILESTONES.md) — M1…M13 mapped to Phases 1–13, each with a checkable gate

## Architecture at a glance

```text
React UI  →  FastAPI  →  Data Layer  →  Environmental Processing  →  Rotation Engine
          →  Scenario Engine  →  Structured Results  →  Optional AI Explanation
```

Two rules define the whole design:

- **The scientific/modeling layer never depends on an LLM.** `backend/engine/` is pure, deterministic,
  offline-runnable, and unit-tested; identical inputs produce byte-identical outputs (`determinism_key`).
- **The LLM is only an explanation layer.** It receives a structured evidence payload and returns prose.
  It cannot add or modify numbers, and the product is fully functional when it is unavailable.

Every number carries provenance with one of four labelled classes:
`OBSERVED` · `DERIVED` · `ASSUMPTION` · `SIMULATED`.

## Planned stack

Frontend: React + TypeScript + Vite, Leaflet, Recharts · Backend: Python 3.12, FastAPI, Pydantic v2,
NumPy, Pandas, GeoPandas/Shapely where needed · No ML in MVP · pytest + ruff + mypy + import-linter.

## Run instructions

Not yet available — implementation begins in Phase 1. Expected entry points after Phase 1:
`uvicorn app.main:app --reload` (backend) and `npm run dev` (frontend), plus
`scripts/fetch_sample_data.py` for a pre-warmed offline demo cache.
## Phase 1 status (backend skeleton)

Run the API locally:

```bash
cd backend
pip install -e ".[dev]"          # or: pip install fastapi "uvicorn[standard]" pydantic-settings numpy pandas pytest httpx ruff import-linter
cp .env.example .env             # optional; sane defaults are built in
uvicorn app.main:app --reload    # http://localhost:8000/api/v1/health · docs at /docs
pytest -p no:libtmux             # run tests (see note below)
lint-imports                     # engine purity contract (no network/LLM imports in engine/)
ruff check .
```

`GET /api/v1/health` → `{"data": {"status":"ok","service":"fieldshift", ...}}` inside the
standard success envelope (docs/03 §0.1). The `-p no:libtmux` flag only works around a
pre-installed third-party pytest plugin in this sandbox; it is not needed on clean machines.
