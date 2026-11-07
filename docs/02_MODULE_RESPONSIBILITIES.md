# FieldShift — Module Responsibilities (Phase 0)

Format per module: **does / does NOT / inputs → outputs / test**.
"Does NOT" is as binding as "does" — it is what keeps modules small and prevents leakage.

---

## A. Application layer — `backend/app/`

### `app/main.py`
- **Does:** builds the FastAPI app, mounts routers, sets CORS, exposes `/health`, serves OpenAPI.
- **Does NOT:** contain any computation or data fetching.
- **Test:** `GET /health` returns 200; OpenAPI document contains exactly the routes in §API contract.

### `app/deps.py`
- **Does:** provide injectable dependencies — settings, provider bundle, curated-table loader, cache dir.
  This is the *only* place where a real network provider vs. a fixture provider is chosen.
- **Does NOT:** compute anything.
- **Test:** with `FIELDSHIFT_OFFLINE=1` the graph resolves to fixture providers (no sockets).

### `app/errors.py` + `app/config.py`
- **Does:** map engine exceptions (`InsufficientDataError`, `OutOfDomainWarning`, `ConstraintViolation`)
  onto the single error envelope and correct HTTP status; parse env settings once.
- **Does NOT:** swallow warnings — engine warnings are attached to successful responses too.

### `app/routers/*`
| Router | Owns | Must not |
|---|---|---|
| `farm.py` | farm-profile validation/persistence, environmental-profile request/response | derive indicators (engine's job) |
| `knowledge.py` | read-only exposure of crop traits, soil fit, compatibility matrix | interpret scores |
| `rotations.py` | generate + baseline scoring | define scoring formulas |
| `scenarios.py` | stress runs, sensitivity sweeps | invent perturbation magnitudes (from curated table) |
| `explain.py` | optional narrative | be required for any other route to succeed |

---

## B. Schemas — `backend/schemas/`

Pydantic v2 models are the **single source of truth for the wire format** (OpenAPI generated from them).
`common.py` defines the cross-cutting types used everywhere:

```python
Provenance       # source_id, class(OBSERVED|DERIVED|ASSUMPTION|SIMULATED), retrieved_at,
                 # resolution, units, method, citation, confidence
Confidence       # level(low|medium|high), reasons[], coverage_pct
FieldWarning     # code, severity(info|warning|blocking), message, field_path
Metric           # value, provenance, warning[]        <- every number is wrapped
```

- **Does:** validate ranges/enums, serialise units, keep contracts versioned (`api_version`).
- **Does NOT:** import from `engine/` (schemas are leaf-level; engine uses its own dataclasses and
  the router adapts). Avoids HTTP concerns leaking into science.

---

## C. Data layer — `backend/data/`

### `data/providers/base.py`
- **Does:** define `Protocol Provider: fetch(query) -> list[Observation]` plus retry/time-out policy
  and a `FixtureProvider` for tests/offline mode.
- **Does NOT:** compute indicators.

### `data/providers/nasa_power.py`
- **Does:** request daily meteorology for a lat/lon box and date range; normalise to SI units;
  tag `source_id="NASA_POWER"`, class=`OBSERVED`.
- **Does NOT:** fill gaps by guessing — missing days stay `NaN` and raise a coverage warning.

### `data/providers/modis_ndvi.py`
- **Does:** retrieve NDVI/EVI composites for the AOI; report pixel count, cloud/post-processing QA.
- **Does NOT:** classify land cover, do image processing, or claim field-level precision beyond resolution.

### `data/providers/soil_ssurgo.py`
- **Does:** obtain texture (sand/silt/clay %), pH, organic carbon/matter, water-holding capacity,
  rooting-limiting layer for the AOI point/polygon; spatial join via GeoPandas.
- **Does NOT:** extrapolate soil beyond mapped extent; if no map unit covers the AOI → `not_computed`.

### `data/providers/climate_normals.py`
- **Does:** supply the 30-year reference normals used as the anomaly baseline (period stated explicitly).
- **Does NOT:** act as a forecast source.

### `data/registry.py`
- **Does:** hold `SOURCE_REGISTRY`: id → title, provider, product ID, resolution, temporal step,
  access URL, licence, citation, retrieval policy, validated domain.
- **Rule:** any `source_id` used anywhere in code must exist here. CI asserts this.
- **Does NOT:** store actual data values.

### `data/loader.py`
- **Does:** cache-or-fetch orchestration, unit normalisation, DataFrame assembly, provenance attachment,
  coverage checks, deterministic ordering (sorted keys) so downstream hashing is stable.
- **Does NOT:** score, rank, or choose scenarios.

### `data/curated/*.csv`
- **Does:** version-controlled static knowledge tables with a `citation` column per row:
  `crop_traits.csv`, `rotation_rules.csv`, `stress_sensitivity.csv`, `scenario_magnitudes.csv`.
- **Rule:** rows without a resolvable citation fail `scripts/validate_dataset.py`.

---

## D. Engine — `backend/engine/` (pure, deterministic, LLM-free)

### `engine/environmental/growing_season.py`
- **Does:** derive the growing-season window (first/last date with T_mean ≥ base °C) and length in days.
- **Inputs:** daily temperature series → **Outputs:** `SeasonWindow(start,end,length_days)` (class=DERIVED).
- **Test:** known synthetic series → exact window; property: monotone in warming.

### `engine/environmental/indicators.py`
- **Does:** compute the derived indicator set used by scoring — heat-sum above base temp per crop group,
  frost/cold-day counts, consecutive dry-spell statistics, seasonal precipitation totals,
  water-supply index (P/PET proxy), NDVI greenness/anomaly summary.
- **Inputs:** normalised observation frames + crop base temperatures → **Outputs:** `EnvironmentalProfile`.
- **Does NOT:** weight or combine indicators into judgments (that is `scorer.py`).
- **Test:** hand-computed fixtures; NaN handling; determinism across two runs.

### `engine/environmental/anomalies.py`
- **Does:** observed − normal differences with sign, magnitude, percentile-of-distribution placement.
- **Does NOT:** attribute cause ("due to climate change") — causality belongs to narrative text only if cited.

### `engine/knowledge/crop_traits.py`
- **Does:** load + validate the trait table (family, season, duration, rooting depth, N role,
  residue/biomass, moisture tolerance band, heat tolerance band, salinity sensitivity, pest-host flags).
- **Does NOT:** accept out-of-range or uncited rows.

### `engine/knowledge/soil_fit.py`
- **Does:** map soil properties × crop requirements → bounded suitability 0–1 per factor
  (texture/drainage, pH, water-holding, rooting depth vs limiting layer) with explicit band functions.
- **Test:** boundary cases at band edges; monotonicity inside bands.

### `engine/knowledge/compatibility.py`
- **Does:** pairwise preceding→following crop rules: family-repeat penalty, N credit after legume,
  shared pest/disease host overlap, residue/soil-structure effect. Returns rule IDs fired.
- **Does NOT:** silently use undocumented rules — every fired rule traces to a `rotation_rules.csv` row.

### `engine/rotation/constraints.py`
- **Does:** hard feasibility filters (no same-family consecutive years unless allowed, fallow limits,
  horizon length, mandatory-crop inclusion, exclusion list).
- **Output:** `feasible: bool, violated_rule_ids: []`.

### `engine/rotation/generator.py`
- **Does:** enumerate candidate rotations over horizon H (default 4 years) from the allowed crop set,
  apply constraints, deduplicate by canonical form (e.g. cyclic equivalence), cap the count deterministically.
- **Does NOT:** optimise/search stochastically. Output order is stable across runs.

### `engine/rotation/scorer.py`
- **Does:** produce per-rotation dimension scores 0–100 for the fixed MVP dimensions:
  `soil_health`, `water_resilience`, `climate_exposure`, `pest_disease_disruption`,
  `operational_risk`, `priority_fit`. Pure functions of (rotation, EnvironmentalProfile, SoilProfile, traits, weights).
- **Does NOT:** aggregate dimensions into an overall ranking (`ranking/aggregate.py`), and does not know scenarios exist.
- **Test:** golden-file scorecard; each dimension independently unit-tested; all inputs documented as DERIVED/ASSUMPTION.

### `engine/scenario/perturbations.py`
- **Does:** apply named, curated deltas to an `EnvironmentalProfile` (e.g. `warm_+2C`,
  `dry_-20pct_growing_season`, `late_frost`, `wet_spring_delay`, `ndvi_decline_recent`) producing
  `class=SIMULATED` profiles + a scenario description card.
- **Does NOT:** exceed the documented magnitude ranges; unknown scenario names are rejected.

### `engine/scenario/stress_runner.py`
- **Does:** re-score all candidate rotations under each scenario; assemble the rotation × scenario matrix.
- **Property:** baseline scenario = identity ⇒ identical scores to `rotations` baseline (asserted in tests).

### `engine/scenario/robustness.py`
- **Does:** compute resilience metrics from the matrix: mean score, worst-case score,
  score variance, rank stability (Spearman/Kendall τ vs baseline ranks), max regret,
  fraction of scenarios in top-k, and a `fragility_flag`.
- **Does NOT:** recompute dimension scores.

### `engine/ranking/aggregate.py`
- **Does:** weighted aggregation of dimensions using farmer priorities; Pareto-front identification;
  final ordering with ties broken deterministically (lexicographic on rotation ID); attach the weight vector.
- **Does NOT:** hide that changing weights changes the order (weights echoed in response).

### `engine/payload/explanation_payload.py`
- **Does:** build the structured evidence bundle: ranked rotations, fired rule IDs, dominant limiting
  factors per dimension, scenario deltas, provenance list, warnings, confidence.
- **This is the ONLY object the LLM may see.** It is also what the UI renders natively.
- **Does NOT:** contain prose.

---

## E. Explanation sidecar — `backend/explain/`

### `explain/narrate.py`
- **Does:** template-prompt the model with the JSON payload; ask for plain-language summary of
  *given* facts; return `{text, payload_hash, model, disclaimer}`. Validates that every number in the
  output appears in the payload (reject otherwise).
- **Does NOT:** import `engine/`, compute, or alter any value. Failure ⇒ route returns
  `503 {code:"EXPLAIN_UNAVAILABLE"}` and the UI falls back to structured rendering.

### `explain/prompts.py`
- **Does:** system prompt forbidding invented data, requiring citation of rule IDs, mandating the
  "relative comparison, not advice" framing.

---

## F. Frontend — `frontend/src/`

| Module | Owns | Must not |
|---|---|---|
| `api/` | generated typed client, error-envelope unwrapping, retries | business logic |
| `state/` | pipeline stages (profile → env → rotations → scenarios → results), local persistence of last run | recompute science |
| `FarmProfileWizard` | AOI draw/upload (GeoJSON), area, crops in/out, priority sliders | call scoring endpoints directly |
| `FieldMap` | Leaflet layers: AOI, soil map units, NDVI raster overlay, legend + resolution note | imply sub-pixel accuracy |
| `EnvironmentalPanel` | normals vs observed, anomalies, coverage/confidence bars | display unlabelled numbers |
| `TimeSeriesChart` | NDVI & met time series, scenario overlay (dashed = SIMULATED) | mix observed/simulated styles |
| `RotationTimeline` | year × crop grid per candidate | reorder years |
| `ScenarioControls` | pick curated scenarios, magnitude within allowed range, reset | free-form unbounded inputs |
| `ComparisonTable` | dimension scores, robustness metrics, rank movement arrows | drop weight/provenance columns |
| `RobustnessScatter` | mean vs worst-case scatter, fragility highlight | present as probability |
| `ProvenanceBadge` | the 4-class badge + tooltip (source, retrieved_at, units, method) | be optional/hidden |
| `ExplanationCard` | narrative + "show structured evidence" toggle | render narrative without the payload available |

---

## G. Scripts & CI

- `scripts/fetch_sample_data.py` — one command to warm the cache for the demo region (documented region only).
- `scripts/validate_dataset.py` — schema + citation completeness for `data/curated/*`; registry/source_id consistency.
- CI: `pytest` (unit + contract + golden), `ruff`, `mypy engine/ --strict`, import-linter purity contract
  (`engine` must not import `app`, `explain`, `requests`, `openai`), `npm run build`.
