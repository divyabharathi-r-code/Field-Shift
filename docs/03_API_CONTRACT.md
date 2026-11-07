# FieldShift — API Contract (Phase 0, v1 draft)

Base URL: `/api/v1` · Content type: `application/json; charset=utf-8` · Auth: none for MVP.
OpenAPI is generated from the Pydantic models in `backend/schemas/`; this document is the human spec.

---

## 0. Conventions

### 0.1 Success envelope
Every 2xx body contains at minimum:

```json
{
  "api_version": "v1",
  "data": { "...": "endpoint-specific payload" },
  "provenance": [ { "source_id": "NASA_POWER", "class": "OBSERVED", "...": "..." } ],
  "warnings": [ { "code": "LOW_COVERAGE", "severity": "warning", "field_path": "precipitation", "message": "12% of days missing" } ],
  "confidence": { "level": "medium", "coverage_pct": 0.88, "reasons": ["soil map unit interpolated"] },
  "run_id": "fs_2026_11_07_a1b2c3",
  "engine_version": "0.1.0",
  "determinism_key": "sha256:…"
}
```

`determinism_key` = hash of normalised inputs + engine version. Same key ⇒ byte-identical result.
This is how we *prove* determinism to judges and how scenario runs stay comparable.

### 0.2 Error envelope (all non-2xx)

```json
{ "error": { "code": "INSUFFICIENT_DATA", "message": "…", "details": {}, "warnings": [] } }
```

| HTTP | code | meaning |
|---|---|---|
| 400 | `VALIDATION_ERROR` | schema/range failure (FastAPI/Pydantic detail attached) |
| 404 | `NOT_FOUND` | unknown rotation_id / scenario_id / farm_id |
| 422 | `OUT_OF_DOMAIN` | inputs outside validated domain (e.g. unsupported climate zone) |
| 424 | `INSUFFICIENT_DATA` | required provider data unavailable → nothing is guessed |
| 503 | `PROVIDER_UNAVAILABLE` | upstream NASA/NOAA outage (client should use cache/offline mode) |
| 503 | `EXPLAIN_UNAVAILABLE` | LLM sidecar down; **not** an error for any other endpoint |

### 0.3 Cross-cutting types

```python
DataClass   = "OBSERVED" | "DERIVED" | "ASSUMPTION" | "SIMULATED"

Provenance  = { source_id: str, class: DataClass, retrieved_at?: date, resolution?: str,
                temporal_step?: str, units?: str, method?: str, citation?: str,
                formula?: str, assumption_rationale?: str, sensitivity_range?: [num, num] }

Metric      = { value: float|null, status: "ok"|"not_computed"|"insufficient_data",
                provenance: Provenance, warnings: FieldWarning[] }

Score       = { dimension: str, value: 0..100, band: "low"|"moderate"|"good",
                drivers: [{factor, contribution, provenance}], provenance: Provenance }
```

Rules: (a) a null value never appears without `status`; (b) every number carries `units`;
(c) `class=SIMULATED` values must additionally carry `scenario_id`.

---

## 1. Endpoints

### `GET /health`
→ `{status:"ok", engine_version, offline_mode: bool, cache_warm: bool, sources_available:[...]}`

---

### 1.1 Farm Profile

#### `POST /farm-profile`
Request:
```json
{
  "name": "North Quarter",
  "geometry": { "type": "Feature", "geometry": {"type":"Polygon","coordinates":[[[…]]]}, "properties": {} },
  "center": { "lat": 41.6, "lon": -93.5 },
  "area_ha": 38.4,
  "current_rotation": ["corn", "soybean"],
  "years_in_current_rotation": 3,
  "allowed_crops": ["corn","soybean","oats","alfalfa","winter_wheat","rye_cover"],
  "excluded_crops": ["rice"],
  "irrigated": false,
  "priorities": { "soil_health": 0.3, "water_resilience": 0.25, "climate_exposure": 0.2,
                  "pest_disease_disruption": 0.15, "operational_risk": 0.1 },
  "horizon_years": 4
}
```
Validation: polygon area > 0; `priorities` sum to 1.0 ± 0.001 (server does NOT silently renormalise —
it returns 400 so the UI shows the discrepancy); `allowed_crops ⊆ crop_traits.csv`;
`horizon_years ∈ [2,6]`; center inside polygon if both supplied.

Response `data`: `{ farm_id, area_ha (computed via Shapely/GeoPandas, provenance DERIVED), center,
echoed profile, geometry_validity }`

#### `GET /farm-profile/{farm_id}` → stored profile or 404.

---

### 1.2 Environmental Profile (NASA-derived)

#### `GET /environmental-profile?farm_id=&start_year=&end_year=`
Response `data`:
```json
{
  "location": {"lat": 41.6, "lon": -93.5},
  "period": {"observed": [2015, 2025], "normal_baseline": [1991, 2020]},
  "growing_season": {
    "start_day_of_year": Metric, "length_days": Metric,
    "base_temp_c": {"value": 10, "provenance": {"class":"ASSUMPTION","assumption_rationale":"…","sensitivity_range":[5,10]}}
  },
  "indicators": {
    "heat_sum_gt_base": Metric, "frost_days": Metric, "cold_snap_events": Metric,
    "max_consecutive_dry_days": Metric, "growing_season_precip_mm": Metric,
    "water_supply_index": Metric, "spring_wet_delay_days": Metric
  },
  "anomalies": {
    "tmean_c": {"observed": Metric, "normal": Metric, "delta": Metric, "percentile": Metric},
    "precip_mm": { "…": "…" },
    "ndvi": {"peak": Metric, "mean_season": Metric, "trend_slope_per_year": Metric,
             "anomaly_vs_normal": Metric}
  },
  "series": {
    "daily_met":     [{"date":"2024-05-01","tmin_c":-1.2,"tmax_c":24.8,"prcp_mm":0,"source_id":"NASA_POWER"}],
    "ndvi_16day":    [{"date":"2024-05-08","ndvi":0.62,"evi":0.41,"qa":"corrected","source_id":"MODIS_NDVI"}]
  },
  "coverage": {"met_days_pct": 0.97, "ndvi_cloud_masked_pct": 0.11, "soil_mapped_pct": 1.0}
}
```
Notes: `series` may be paginated/downsampled (`?series=daily|monthly|none`). NDVI is reported with
its native pixel resolution and AOI-pixel count — the UI must show that footprint on the map.

#### `GET /soil-profile?farm_id=`
`data`: `{ texture_pct{sand,silt,clay}, drainage_class, ph, organic_carbon_pct, water_holding_capacity_mm,
rooting_limiting_depth_cm, map_unit_symbol, sourced_from }` — each a `Metric`; anything unmapped is
`status:"not_computed"` (never 0).

---

### 1.3 Knowledge

- `GET /knowledge/crops` → trait table rows incl. `citation` per row.
- `GET /knowledge/crops/{crop_id}` → single crop + soil-fit factors for a given `farm_id`.
- `GET /knowledge/compatibility?crops=a,b,c` → pairwise matrix; each cell `{score, fired_rule_ids[], provenance}`.
- `GET /knowledge/rules` → all rotation rules with rationale + citation.
- `GET /knowledge/scenarios` → curated scenario catalogue (id, label, affected indicators, allowed magnitude range, description, citation).

---

### 1.4 Rotations

#### `POST /rotations/generate`
`{ farm_id, horizon_years?, max_candidates?=40 }` →
`data: { rotations: [{rotation_id, years:["corn","soybean","oats","alfalfa"], canonical_form, feasible:true}],
count_generated, count_filtered_out: {by_rule_id: n}, note: "enumeration is deterministic" }`

#### `POST /rotations/score`
`{ farm_id, rotation_ids? (default all), weights? (default farm priorities) }` →
```json
data: {
  "weights_used": {"soil_health":0.3, "...":0.1},
  "results": [{
     "rotation_id": "r0007",
     "years": ["corn","soybean","oats","alfalfa"],
     "scores": { "soil_health": Score, "water_resilience": Score, "climate_exposure": Score,
                 "pest_disease_disruption": Score, "operational_risk": Score },
     "overall": {"value": 68.4, "rank": 2, "pareto_front": true},
     "fired_rules": ["RR_LEGUME_N_CREDIT","RR_FAMILY_GAP_OK"],
     "limiting_factors": ["water_supply_index"],
     "provenance": ["..."], "warnings": []
  }]
}
```
`Score.drivers` must make the score auditable: which factor contributed how much, and whether that
factor is DERIVED or ASSUMPTION.

---

### 1.5 Scenarios (stress testing)

#### `POST /scenarios/stress`
```json
{ "farm_id": "…", "rotation_ids": ["r0001","r0007"], "scenario_ids": ["warm_plus2c","dry_minus20_gs","late_frost"],
  "custom_overrides": [ { "indicator": "growing_season_precip_mm", "mode": "relative", "delta": -0.2 } ] }
```
Response `data`:
```json
{
  "scenarios": [{ "scenario_id":"warm_plus2c", "label":"Warm +2 °C", "class":"SIMULATED",
                  "deltas":{"tmean_c":"+2.0"},"description":"…","citation":"…","is_forecast": false }],
  "matrix": [{ "rotation_id":"r0007","scenario_id":"baseline","overall":68.4,"rank":2,"scores":{...} }],
  "robustness": [{ "rotation_id":"r0007","mean_score":64.1,"worst_case":51.9,"score_std":5.8,
                    "rank_stability_tau":0.86,"max_regret":9.2,"top_k_share":0.67,
                    "fragility_flag":false,"classification":"robust" }],
  "banner": "Simulated counterfactuals for comparison only — not forecasts."
}
```
Constraint: `custom_overrides` magnitudes are clamped to the curated allowed range; exceeding it → 422.

#### `POST /scenarios/sensitivity`
`{ farm_id, sweep: {param:"weights.soil_health", from:0, to:0.6, steps:7} }` →
`data: { sweeps:[{param_value, ranking:[rotation_id,…]}], rank_change_points:[…], interpretation_keys:[…] }`
(Used by the UI to show *when* the answer flips — the heart of the product.)

---

### 1.6 Comparison & Explanation

#### `GET /comparison?farm_id=&scenario_ids=&k=5`
Bundled view for the results screen: baseline + stressed rankings side-by-side, robustness metrics,
weight vector, provenance list, warnings. Equivalent to composing 1.4 + 1.5 (kept as one call to
simplify the UI and guarantee a consistent snapshot).

#### `POST /explain`
Request: `{ "payload": <ExplanationPayload>, "language": "en", "audience": "farmer" }`
Response `data`: `{ text, payload_hash, model, disclaimer, structured_reference: <same payload> }`
Rules: numbers in `text` must exist in `payload` (server-side check); if the sidecar is unconfigured
→ `503 EXPLAIN_UNAVAILABLE`. The UI always renders `structured_reference`, never narrative alone.

---

## 2. Endpoint summary

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/health` | readiness, offline/cache state | 1 |
| POST | `/farm-profile` | create/validate profile | 3 |
| GET | `/farm-profile/{id}` | fetch profile | 3 |
| GET | `/environmental-profile` | NASA-derived indicators + anomalies | 2/6 |
| GET | `/soil-profile` | local soil information | 2/4 |
| GET | `/knowledge/crops` , `/knowledge/crops/{id}` | crop traits | 4 |
| GET | `/knowledge/compatibility` | pairwise rotation rules | 4/5 |
| GET | `/knowledge/rules` | rule catalogue + citations | 4 |
| GET | `/knowledge/scenarios` | scenario catalogue | 6 |
| POST | `/rotations/generate` | enumerate candidates | 5 |
| POST | `/rotations/score` | baseline multi-criteria scoring | 5 |
| POST | `/scenarios/stress` | stress test across scenarios | 6 |
| POST | `/scenarios/sensitivity` | priority/parameter sweeps | 6 |
| GET | `/comparison` | consistent snapshot for results screen | 7 |
| POST | `/explain` | optional LLM narrative | 10 |

## 3. Contract tests (must exist before implementation is "done")

1. OpenAPI snapshot diff fails CI on undocumented route/schema change.
2. Every response validates against its schema; every `Metric` has `provenance.class`.
3. No `null` numeric without `status != "ok"`.
4. Repeating any request twice yields identical `determinism_key` and body.
5. Engine purity: import-linter rejects `engine → app|explain|requests|openai`.
6. `EXPLAIN_UNAVAILABLE` never affects `/comparison` availability (integration test with sidecar disabled).
