# FieldShift — Architecture & Folder Structure (Phase 0)

## 1. Layered architecture (dependency direction is strict)

```text
┌──────────────────────────────────────────────────────────────┐
│  React UI (frontend/)                                        │
│  farm profile wizard · map · charts · scenario slider ·      │
│  comparison table · provenance badges                        │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP/JSON (OpenAPI-typed client)
┌───────────────────────────▼──────────────────────────────────┐
│  FastAPI application layer (backend/app/)                    │
│  routers · request validation (Pydantic) · error envelope    │
│  NO science here                                             │
└───────────────────────────┬──────────────────────────────────┘
                            │ plain Python dataclasses / dicts
┌───────────────────────────▼──────────────────────────────────┐
│  ENGINE — pure, deterministic, LLM-free (backend/engine/)    │
│  data → environmental → knowledge → rotation → scoring →     │
│  scenarios → ranking → explanation-payload                   │
└───────────────────────────┬──────────────────────────────────┘
                            │ typed records
┌───────────────────────────▼──────────────────────────────────┐
│  DATA LAYER (backend/data/)                                  │
│  providers (NASA/NOAA/soil) · on-disk cache · curated        │
│  static tables · provenance registry                         │
└──────────────────────────────────────────────────────────────┘

Sidecar (optional, non-blocking):  backend/explain/  -> LLM narrative
Never imported by engine/. Engine never imports explain/.
```

**Key rule:** `engine/` has **zero** network access and **zero** LLM imports. It receives
already-fetched, already-normalised records. This makes it runnable in tests with no API key,
no internet, and no non-determinism.

## 2. Proposed folder structure

```text
fieldshift/
├── README.md
├── docs/                          # source of truth for contracts & assumptions
│   ├── 00_PROJECT_RULES.md
│   ├── 01_ARCHITECTURE_AND_FOLDERS.md   (this file)
│   ├── 02_MODULE_RESPONSIBILITIES.md
│   ├── 03_API_CONTRACT.md
│   ├── 04_DATA_FLOW.md
│   ├── 05_DATA_SOURCES_AND_PROVENANCE.md
│   ├── 06_MODEL_ASSUMPTIONS.md
│   └── 07_MILESTONES.md
│
├── backend/
│   ├── pyproject.toml
│   ├── app/                       # HTTP layer only
│   │   ├── main.py                # FastAPI factory, CORS, OpenAPI
│   │   ├── deps.py                # dependency injection (providers, config)
│   │   ├── errors.py              # single error envelope + exception handlers
│   │   ├── config.py              # env settings, cache dir, API keys (optional)
│   │   └── routers/
│   │       ├── health.py
│   │       ├── farm.py            # POST /farm-profile, GET /environmental-profile
│   │       ├── knowledge.py       # crops, soil, compatibility matrix
│   │       ├── rotations.py       # generate + score baseline
│   │       ├── scenarios.py       # stress testing, sensitivity sweep
│   │       └── explain.py         # optional LLM narrative (only LLM route)
│   │
│   ├── schemas/                   # Pydantic v2 models = the wire contract
│   │   ├── common.py              # Provenance, Units, Confidence, Warning
│   │   ├── farm.py
│   │   ├── environment.py
│   │   ├── knowledge.py
│   │   ├── rotation.py
│   │   ├── scenario.py
│   │   └── results.py             # Scorecard, ComparisonResponse
│   │
│   ├── engine/                    # PURE SCIENCE. No I/O, no LLM, no globals.
│   │   ├── environmental/
│   │   │   ├── growing_season.py  # season window from temperature series
│   │   │   ├── indicators.py      # heat-sum, cold days, dry spells, water supply
│   │   │   └── anomalies.py       # obs vs 30-yr normal, NDVI/EVI anomaly stats
│   │   ├── knowledge/
│   │   │   ├── crop_traits.py     # load/validate curated trait table
│   │   │   ├── soil_fit.py        # texture/pH/organic-matter suitability
│   │   │   └── compatibility.py   # pairwise rotation rules (family, N, pests)
│   │   ├── rotation/
│   │   │   ├── generator.py       # enumerate legal rotations for horizon H
│   │   │   ├── constraints.py     # hard rules: family repeat, host crops, fallow
│   │   │   └── scorer.py          # multi-criteria dimension scores (0-100)
│   │   ├── scenario/
│   │   │   ├── perturbations.py   # apply deltas to an EnvironmentalProfile
│   │   │   ├── stress_runner.py   # re-score all rotations across scenarios
│   │   │   └── robustness.py      # rank-stability, worst-case, regret metrics
│   │   ├── ranking/
│   │   │   └── aggregate.py       # weighted aggregation + Pareto + fragility flags
│   │   └── payload/
│   │       └── explanation_payload.py  # structured evidence bundle for the LLM/UI
│   │
│   ├── data/
│   │   ├── providers/             # thin, individually testable fetchers
│   │   │   ├── nasa_power.py      # NASA POWER (daymet* daily met) — OBSERVED
│   │   │   ├── modis_ndvi.py      # MODIS NDVI/EVI via Worldview/CMR — OBSERVED
│   │   │   ├── soil_ssurgo.py     # SSURGO / gNATSO soil tabular + raster mirror
│   │   │   ├── climate_normals.py # NOAA/NCEI normals used as the reference baseline
│   │   │   └── base.py            # Provider protocol: fetch() -> list[Observation]
│   │   ├── cache/                 # content-addressed parquet/json cache (gitignored)
│   │   ├── curated/               # version-controlled static tables (CSV/YAML)
│   │   │   ├── crop_traits.csv
│   │   │   ├── rotation_rules.csv
│   │   │   └── stress_sensitivity.csv
│   │   ├── registry.py            # SOURCE_REGISTRY: id -> citation, licence, resolution
│   │   └── loader.py              # read cache-or-fetch, attach provenance, normalise units
│   │
│   ├── explain/                   # OPTIONAL LLM SIDECAR (isolated)
│   │   ├── narrate.py             # payload -> text; numbers are READ-ONLY passthrough
│   │   └── prompts.py             # template that forbids inventing facts
│   │
│   └── tests/
│       ├── unit/                  # one file per engine module
│       ├── contract/              # schema round-trip + OpenAPI snapshot
│       ├── golden/                # frozen input->score fixtures (regression)
│       └── fixtures/
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api/                   # generated OpenAPI client + typed hooks
│   │   ├── components/
│   │   │   ├── FarmProfileWizard.tsx
│   │   │   ├── FieldMap.tsx        # Leaflet or MapLibre
│   │   │   ├── EnvironmentalPanel.tsx
│   │   │   ├── TimeSeriesChart.tsx # Recharts
│   │   │   ├── RotationTimeline.tsx
│   │   │   ├── ScenarioControls.tsx
│   │   │   ├── ComparisonTable.tsx
│   │   │   ├── RobustnessScatter.tsx
│   │   │   ├── ProvenanceBadge.tsx # OBSERVED/DERIVED/ASSUMPTION/SIMULATED
│   │   │   └── ExplanationCard.tsx
│   │   ├── state/                 # pipeline store: profile -> results
│   │   ├── lib/                   # formatting, units, colour scales
│   │   └── types/                 # mirrors backend/schemas (generated)
│   └── public/data/               # sample farm GeoJSON for offline demo
│
├── scripts/
│   ├── fetch_sample_data.py       # populate backend/data/cache for the demo region
│   └── validate_dataset.py        # assert curated CSVs match schema + citations
├── data_downloads/                # raw provider files (gitignored)
├── .github/workflows/ci.yml       # pytest + ruff + npm build
└── .gitignore
```

## 3. Architectural decisions and rationale

**D1 — Engine is a pure function library, not a service.**
`engine/*` modules take dataclasses and return dataclasses. No FastAPI, no HTTP, no filesystem.
*Rationale:* satisfies "scientific layer must not depend on an LLM" and makes determinism
testable; the same code path runs in the API, in a CLI, and in golden-file regression tests.

**D2 — Providers sit below the engine, behind a `Provider` protocol.**
Fetching is injected (`app/deps.py`), so tests substitute a fixture provider.
*Rationale:* keeps network flakiness out of the science; enables fully offline demo mode.

**D3 — Deterministic enumeration instead of optimisation.**
Rotations are *enumerated* under hard constraints and then *scored*; we do not solve for an
optimum with an evolutionary/ML search.
*Rationale:* reproducible, explainable, and honest about being a comparison rather than a
prediction. scikit-learn is deliberately absent from MVP; if later introduced (e.g. clustering
of analogue climates) it must be justified in writing and kept out of the scoring path.

**D4 — Scores are relative, always reported with their weight vector.**
Every result carries the farmer-priority weights used, so changing priorities visibly changes
the ranking — which *is* the product's core demonstration.

**D5 — Provenance is a first-class field, not a comment.**
`Provenance {source_id, class, retrieved_at, resolution, units, method, confidence}` travels
with every number into the JSON response and renders as a badge in the UI.

**D6 — Cache-first, content-addressed data layer.**
Raw provider responses are stored keyed by request hash; derived frames as Parquet.
*Rationale:* NASA API latency/quota cannot break the judging demo; identical cache ⇒ identical
results for every run of the demo.

**D7 — One error envelope.** All failures return
`{error:{code,message,details,warning[]}}` with machine-readable codes so the UI can render
actionable messages instead of stack traces.

**D8 — LLM sidecar is optional and additive.** If `explain/` is unavailable or keyless, the UI
still renders the full structured evidence bundle. The narrative is cached by payload hash.
*Rationale:* the tool must remain useful and verifiable with the LLM switched off.

## 4. Technology choices (MVP)

| Layer | Choice | Why / note |
|---|---|---|
| Frontend | React + TypeScript + Vite | typed against the OpenAPI schema |
| Maps | **Leaflet** (default) | simpler for MVP polygon + point; MapLibre only if vector tiles/3D needed |
| Charts | Recharts | sufficient for time series, radar, scatter |
| State | lightweight store (Zustand) | linear pipeline, no Redux ceremony |
| Backend | Python 3.12 + FastAPI + Pydantic v2 | async, auto OpenAPI |
| Numerics | NumPy + Pandas | indicator maths, tabular joins |
| Geospatial | GeoPandas/Shapely **only where needed** | AOI area, polygon→point sampling, soil spatial join |
| ML | none in MVP | see D3 |
| Tests | pytest, hypothesis (property tests), golden files | determinism guard |
| Quality | ruff + mypy (engine at strict) | purity enforced by import-linter contract |
