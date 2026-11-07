# FieldShift — Development Milestones (Phase 0)

One phase per row group. **Gate** = objective, checkable exit criterion. No phase starts before the
previous gate passes. Each phase ends with a commit + green CI. Estimated effort assumes one
developer working through the hackathon window; items marked *(cut)* are the first to drop if time
runs short — they never block the core question.

---

## M0 · Plan approved *(this document set)*
- Deliverables: rules, architecture, module responsibilities, API contract, data flow, source list, assumption register.
- **Gate:** team agrees folder structure + contracts; no implementation code written yet. ✅ requested now.

## M1 · Repository + backend skeleton → *Phase 1*
- Create folders from `01_ARCHITECTURE_AND_FOLDERS.md`; `.gitignore`; `backend/pyproject.toml`
  (fastapi, uvicorn, pydantic v2, numpy, pandas, pytest, ruff, mypy); `frontend/` scaffold (Vite + React + TS).
- `app/main.py` with `/health`, error envelope, config, offline flag; empty routers registered.
- Import-linter purity contract in place (`engine` cannot import app/explain/network clients).
- **Gate:** `pytest` runs (trivially), `GET /health` returns envelope with `offline_mode`, OpenAPI JSON served at `/openapi.json`.

## M2 · Data layer → *Phase 2*
- `registry.py` with SourceRecord schema; providers behind `Provider` protocol + `FixtureProvider`.
- Content-addressed cache + loader (unit normalisation, coverage %, provenance attachment).
- Verify candidate sources against live endpoints/downloads; save samples to `data_downloads/`;
  mark each `verification.status`. Remove anything unverifiable.
- **Gate:** every shipped source_id is `verified` with URL + units + resolution + licence recorded;
  loader works fully offline from cache; test asserts no unlabelled provenance escapes.

## M3 · Farm profile → *Phase 3*
- `schemas/farm.py` validation (geometry, area via GeoPandas/Shapely, crops ⊆ table, weights sum = 1 strict).
- `POST/GET /farm-profile`; in-memory/file store for MVP; 400 on bad weights (no silent renormalise).
- **Gate:** contract tests pass incl. rejection cases; area computation documented as DERIVED.

## M4 · Crop / soil knowledge → *Phase 4*
- Curated CSVs with per-row citations; `crop_traits.py` validation; `soil_fit.py` band functions;
  `compatibility.py` rule engine returning fired rule IDs; `GET /knowledge/*`.
- Fill A-06…A-09 in the assumptions register with real citations.
- **Gate:** `scripts/validate_dataset.py` green (no uncited rows); compatibility matrix symmetric-tested;
  soil endpoint returns `not_computed` where unmapped (test with an unmapped AOI).

## M5 · Rotation engine → *Phase 5*
- `generator.py` enumeration + canonical dedupe + deterministic cap; `constraints.py` hard rules;
  `scorer.py` five weight-free dimensions with `drivers[]`; golden-file scorecard committed.
- Finalise dimension formulas + normalisation anchors in `06_MODEL_ASSUMPTIONS.md` (worked example).
- **Gate:** same input ⇒ byte-identical `determinism_key` and scorecards across two runs; all scores ∈ [0,100];
  every driver traceable to a trait/rule ID; unit tests per dimension.

## M6 · Stress simulation → *Phase 6*
- `perturbations.py` with curated scenario catalogue (`GET /knowledge/scenarios`); `stress_runner.py`;
  `robustness.py` metrics; `POST /scenarios/stress` + `/scenarios/sensitivity`.
- **Gate:** identity-scenario property test equals baseline exactly; override magnitudes clamped/rejected
  outside allowed range; rank-stability and regret computed on a synthetic matrix with known answers.

## M7 · FastAPI integration → *Phase 7*
- Wire all routers end-to-end; `GET /comparison` snapshot endpoint; consistent warnings/confidence propagation;
  pagination/downsample options for series; OpenAPI snapshot test committed.
- **Gate:** full pipeline callable over HTTP for the demo region; contract tests §3 of `03_API_CONTRACT.md` pass;
  repeated calls identical; no route depends on the LLM.

## M8 · React UI → *Phase 8*
- Wizard → map → environmental panel → rotation timeline → comparison table → results screen; typed client
  generated from OpenAPI; state machine from `04_DATA_FLOW.md` §5; `ProvenanceBadge` on every number.
- **Gate:** a judge can go from drawing a field to a ranked comparison without touching code;
  observed vs derived vs assumption vs simulated visually distinguishable; build passes.

## M9 · NASA data visualization → *Phase 9*
- Leaflet layers (AOI, NDVI raster overlay with pixel footprint, soil map units); Recharts time series
  (NDVI + met, normals vs observed, anomaly bars); scenario overlays rendered dashed + labelled SIMULATED;
  RobustnessScatter (mean vs worst-case) and rank-movement view; sensitivity "rank flip point" chart.
- **Gate:** no chart mixes data classes without styling/legend distinction; resolutions displayed;
  screenshots captured for the submission package.

## M10 · AI explanation → *Phase 10*
- `explain/narrate.py` + prompts; numbers-in-text validation; caching by payload hash; graceful 503 fallback.
- **Gate:** with sidecar disabled the product is fully usable (test); narrative contains no number absent
  from payload (automated check); disclaimer rendered; engine has zero LLM imports (import-linter).

## M11 · Testing + validation → *Phase 11*
- Unit + contract + golden suites complete; property tests; sensitivity sweep over all A-xx ranges;
  citation review; documented limitations page; edge cases (missing soil map, cloud-heavy NDVI,
  non-polygon farm, extreme weights).
- **Gate:** CI green with coverage threshold on `engine/`; determinism keys stable; assumption-sensitivity
  summary written into docs and surfaced in UI confidence.

## M12 · Polish + demo → *Phase 12*
- One-command offline demo (`scripts/fetch_sample_data.py` pre-warmed + `FIELDSHIFT_OFFLINE=1`);
  seeded sample farms; loading/error states; copy tuned to the core question; performance pass;
  3-minute demo script + narration; README quickstart; attribution/licence page.
- **Gate:** rehearsed demo runs with network off; no console errors; all provenance badges present.

## M13 · Submission → *Phase 13*
- Final artefacts: repo tag, PDF/summary of method + assumptions + data sources, screenshot set,
  demo video, project description aligned to challenge criteria, credits & dataset attributions.
- **Gate:** checklist signed off: (a) core question answered visibly, (b) engine LLM-free proof,
  (c) every data source verified & cited, (d) four data classes distinguishable in UI,
  (e) limitations stated, (f) reproducible run instructions.

---

## Cut line (if time runs out)
Priority order to protect: M1–M7 (working, honest engine + API) > M8 (UI path) > M9 (visual polish)
> M10 (LLM narrative) > M11 extras. The MVP that answers the core question is:
**profile → environmental indicators → generated rotations → scored → stressed under ≥3 scenarios →
ranked comparison with robustness flags and provenance.** Everything else is enhancement.
