# FieldShift — Model Assumptions Register (Phase 0 skeleton)

Every constant used by `backend/engine/` must appear here with a rationale and a sensitivity range.
Class = **ASSUMPTION** unless noted. Placeholders below are marked `TBD — calibrate in Phase 4/5`;
they are **not** shipped values. No placeholder may reach the demo path.

| ID | Constant / rule | Value | Class | Rationale & citation | Sensitivity tested | Status |
|---|---|---|---|---|---|---|---|
| A-01 | Growing-season base temperature for cool-season group | TBD °C | ASSUMPTION | agronomic base-temp convention, cite source | 5–10 °C sweep | ☐ |
| A-02 | Growing-season base temperature for warm-season group | TBD °C | ASSUMPTION | as above | 8–12 °C sweep | ☐ |
| A-03 | Season start rule: first of ≥n consecutive days T_mean ≥ base | n = TBD | ASSUMPTION | avoids single-day noise | n ∈ {3,5,7} | ☐ |
| A-04 | Dry-spell definition: consecutive days with P < threshold | TBD mm | ASSUMPTION | wet-day threshold convention | 0.5–2.0 mm | ☐ |
| A-05 | Water-supply proxy (P/PET formulation) | TBD | ASSUMPTION | which PET method; documented limitation | Hargreaves vs P-only | ☐ |
| A-06 | Rooting depth per crop | TBD cm | ASSUMPTION | crop trait table citation | ±20 % | ☐ |
| A-07 | Legume N credit to following crop | TBD % | ASSUMPTION | rotation-study citation | 0 → upper bound | ☐ |
| A-08 | Same-family consecutive-year penalty weight | TBD | ASSUMPTION | pest/disease-cycle rationale + citation | 0 → 2× | ☐ |
| A-09 | Soil suitability band shapes (pH, texture, drainage) | TBD | ASSUMPTION | tolerance ranges from cited guides | band-edge shifts | ☐ |
| A-10 | Dimension score normalisation (0–100 mapping) | TBD | METHOD | linear min-max on stated reference range | alternative anchors | ☐ |
| A-11 | Robustness classification thresholds (`fragility_flag`) | TBD | ASSUMPTION | chosen so that "top-k share" and rank τ are interpretable | threshold sweep | ☐ |
| A-12 | NDVI anomaly reference years | TBD | ASSUMPTION | period choice affects anomaly magnitude | window length | ☐ |

## Scoring dimensions — definition contract (MVP set)

For each dimension we fix, before coding: the indicators it consumes, the formula shape, the
reference range for normalisation, and its dominant data class. Formulas are finalised in Phase 5
and recorded here with a worked example.

| Dimension | Consumes | Direction | Dominant class |
|---|---|---|---|
| `soil_health` | soil fit per year, residue/biomass contribution, legume N credit, erosion-prone sequence exposure | higher = better soil-condition trajectory | DERIVED × ASSUMPTION |
| `water_resilience` | rooting depth vs water-holding capacity, dry-spell exposure, water-supply index, irrigation flag | higher = less water-limited under local supply | DERIVED × ASSUMPTION |
| `climate_exposure` | heat-sum match to crop duration, hot-spell sensitivity, frost exposure, season-length mismatch | higher = better match between crop needs and observed/anomalous climate | DERIVED |
| `pest_disease_disruption` | family-repeat gaps, shared-host overlap count across sequence | higher = more disruption of pest/disease cycles | ASSUMPTION (rule-based) |
| `operational_risk` | machinery/labour windows overlap, planting-window tightness, harvest-date collision within the sequence | higher = fewer scheduling conflicts | ASSUMPTION |
| `priority_fit` | weighted aggregation of the five above using farmer weights | reported separately from raw dimensions so weights are visible | DERIVED |

Note: `priority_fit` is produced by `ranking/aggregate.py`, not by `scorer.py` — the scorer stays
weight-free so that dimension scores remain comparable across different farmers' priorities.

## Deliberate simplifications (stated so we do not overclaim)

1. Year-grain scoring, not daily process-based growth simulation. We compare *exposure and fit*,
   never predict yield.
2. Single-field scope in MVP (no whole-farm allocation, no economics).
3. Rotation rules are literature-derived heuristics, encoded as auditable rule IDs — not fitted models.
4. Climate anomalies use a fixed 30-year normal period; changing the period changes anomaly values,
   and that fact is surfaced in the UI rather than hidden.
5. Scenario perturbations are applied to derived indicators directly (transparent deltas), not through
   a coupled atmosphere-crop model. This is why they are labelled SIMULATED counterfactuals.

## Validation plan (Phase 11)

- Golden-file regression on a frozen demo region input → exact scorecard hashes.
- Property tests: scores bounded 0–100; monotonicity where declared; identity scenario ⇒ baseline equality;
  permutation-invariance of year order only where intended.
- Sensitivity analysis over every A-xx assumption range; report which dimensions are assumption-sensitive.
- Expert review pass on `crop_traits.csv` / `rotation_rules.csv` citations.
- Sanity comparison of generated rotations against locally common rotations (qualitative, documented).
