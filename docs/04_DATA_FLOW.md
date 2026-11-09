# FieldShift — Data Flow (Phase 0)

## 1. End-to-end pipeline (single request path)

```text
USER (React UI)
 │
 │ ① draw/upload field polygon · pick crops · set priorities (sliders, sum = 1)
 ▼
POST /farm-profile ─────────────────► schemas/farm.py validation
 │                                     · geometry valid? area_ha via GeoPandas/Shapely
 │                                     · allowed_crops ⊆ curated crop table
 │                                     · weights sum to 1 (400 if not — no silent renormalise)
 ▼
FarmProfile {farm_id, geometry, center, allowed_crops, priorities, horizon_years}
 │
 │ ②  GET /environmental-profile?farm_id=   &   GET /soil-profile?farm_id=
 ▼
data/loader.py  ── cache hit? ── yes ─► read Parquet/JSON from data/cache/
 │                     │
 │                     no ─► providers: NASA_POWER (daily met) · MODIS_NDVI (16-day composite)
 │                            · SOIL (SSURGO/gNATSO) · CLIMATE_NORMALS (30-yr baseline)
 │                            each returns list[Observation] + Provenance(class=OBSERVED)
 ▼
Normalised frames (SI units, sorted dates, NaN preserved, coverage %)
 │
 │ ③  ENGINE (pure): engine/environmental/*
 ▼
EnvironmentalProfile  ← growing_season.py → SeasonWindow (DERIVED)
                        indicators.py     → heat-sum, frost days, dry spells, GS precip,
                                            water-supply index, spring wet delay (DERIVED)
                        anomalies.py      → observed − normal, delta, percentile (DERIVED)
SoilProfile           ← knowledge/soil_fit inputs prepared here (OBSERVED per attribute)
 │
 │ ④  KNOWLEDGE (curated, versioned): engine/knowledge/*
 ▼
CropTraitTable (ASSUMPTION-class where literature ranges are collapsed to a band)
SoilFitMatrix       crop × soil factor → suitability 0..1
CompatibilityMatrix prev crop → next crop → score + fired rule IDs
 │
 │ ⑤  ROTATION ENGINE: engine/rotation/*
 ▼
CandidateRotations[]  generator.enumerate(crop_set, H=4y) → constraints.filter()
                      → canonical dedupe → deterministic order → ≤ max_candidates
Scorecards[]          scorer.score(rotation, EnvProfile, SoilProfile, traits)
                      → 5 dimension Scores with drivers[] + provenance + warnings
 │
 │ ⑥  SCENARIO / STRESS ENGINE: engine/scenario/*
 ▼
ScenarioProfiles[]    perturbations.apply(EnvProfile, scenario_id)  (class=SIMULATED)
StressMatrix          stress_runner: rotations × scenarios → overall + dimension scores
Robustness[]          robustness.compute(matrix) → mean, worst-case, std,
                      rank_stability_tau, max_regret, top_k_share, fragility_flag
 │
 │ ⑦  RANKING: engine/ranking/aggregate.py
 ▼
RankedComparison      weighted overall using priorities_used, Pareto front,
                      baseline rank vs stressed rank, Δrank arrows, tie-break by rotation_id
 │
 │ ⑧  PAYLOAD: engine/payload/explanation_payload.py
 ▼
ExplanationPayload { ranked rotations, fired_rules[], limiting_factors[], scenario deltas,
                     provenance[], warnings[], confidence[], assumptions[], disclaimer }
 │
 ├──────────────► ⑨ GET /comparison response ──► React renders natively (tables, charts, map)
 │
 └──────────────► ⑩ POST /explain (OPTIONAL sidecar, backend/explain/)
                    payload → narrative text; numbers validated against payload;
                    failure ⇒ 503 EXPLAIN_UNAVAILABLE ⇒ UI shows structured evidence only
```

**Direction is one-way.** No stage reads from a later stage. The LLM branch (⑩) is a leaf: nothing
downstream of it feeds back into the numbers.

### 1.1 Experimental NASA POWER endpoint

`GET /api/v1/environmental/daily` is an additive read-only path. The caller supplies coordinates
and an inclusive date range; FastAPI validates the query before a `DataQuery` is passed to the
NASA POWER provider. `FS_NASA_POWER_ENABLED` defaults to `false`; while disabled, the endpoint
returns `503 SOURCE_DISABLED` without constructing the provider. When enabled, the configured
offline flag is passed to the provider: a cache hit can serve the request, while a cache miss in
offline mode raises `503 PROVIDER_UNAVAILABLE` and does not make a network request.

The response contains normalized daily observations and full provider provenance, including
`source_type="PROVIDER_GRIDDED"`. Missing provider values remain `null` with a missing status.
This route does not derive environmental indicators and does not imply farm-station measurements.
NASA POWER remains marked unverified; enabling the experimental gate does not change that status.

## 2. State transitions and data classes at each hop

| Hop | Artifact produced | Dominant data class | What may NOT happen here |
|---|---|---|---|
| ① | FarmProfile | USER INPUT (+ DERIVED area) | server-side guessing of missing farm facts |
| ② | ObservationFrames | OBSERVED | imputation presented as observation |
| ③ | EnvironmentalProfile | DERIVED | any weighting or judgement |
| ④ | Knowledge tables | ASSUMPTION + cited | uncited coefficients |
| ⑤ | Scorecards | DERIVED×ASSUMPTION | aggregation into "the answer" |
| ⑥ | StressMatrix, Robustness | SIMULATED | presenting scenarios as forecasts |
| ⑦ | RankedComparison | DERIVED | hiding the weight vector |
| ⑧ | ExplanationPayload | mixed, labelled | prose |
| ⑨ | UI render | display | unlabelled numbers |
| ⑩ | Narrative | derived text | new numbers, new facts, causal claims |

## 3. Caching & determinism flow

```text
request params (farm_id, years, scenario_ids, weights, engine_version)
   → canonical JSON (sorted keys, rounded floats to declared precision)
   → sha256 = determinism_key
   → cache/{determinism_key}.json present? return it : compute then write
```
- Provider responses cached separately under `raw/{provider}/{request_hash}` so a re-run after an
  upstream change still reproduces the demo (pin retrieval date in `registry`).
- Golden tests store `determinism_key` values; a change in them requires an explicit diff review,
  which makes every behavioural change of the science visible in the PR.

## 4. Failure / degradation flow

```text
provider unreachable ──► offline_mode? use cache ──► else 503 PROVIDER_UNAVAILABLE
required indicator missing ──► Metric.status="insufficient_data"
                              ──► dependent dimension: Score = not_computed
                              ──► confidence.level ↓ ; warning attached ; UI badge
outside validated domain (e.g. tropical rice farm on MVP trait table)
        ──► 422 OUT_OF_DOMAIN with explicit reason (never silently extrapolate)
LLM unavailable ──► /explain 503 ──► UI unaffected (structured evidence always available)
```

## 5. Frontend data flow (state machine)

```text
idle → profiling → environment_loading → environment_ready
     → generating → scored(baseline) → stressing → compared → explained(optional)
                ↘ error(code, retryable?)              ↘ weights_changed → re-score (client keeps payload)
```
Rules: the client never recomputes science locally; sliders that change **weights** call
`/rotations/score` (cheap, pure) while sliders that change **scenarios** call `/scenarios/stress`;
all displayed numbers come from the response body, never from frontend math.
