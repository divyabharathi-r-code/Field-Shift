# FieldShift — Project Rules (Phase 0)

**Challenge:** NASA Space Apps Challenge 2026 — "Field Shift: Adapting Farms with NASA Data"

---

## 1. Core concept

FieldShift is a **transparent decision-support and scenario-exploration tool**. It combines
NASA Earth-observation data, local soil information, crop characteristics, and farmer
priorities to explore **resilient crop-rotation strategies**.

The core question is **NOT**:

> "What crop should the farmer plant?"

The core question **IS**:

> "Which crop rotation remains more resilient when environmental conditions and farmer
> priorities change?"

We therefore never present a single "best crop". We present **ranked rotation strategies**,
each scored across multiple dimensions, and we show **how those rankings move** when the
environment or the farmer's priorities are perturbed. A strategy that wins under one setting
but collapses under a small shift is flagged as *fragile*; a strategy that stays competitive
across many settings is flagged as *robust*.

## 2. Product flow

```text
Farm Profile
  -> NASA Environmental Profile
  -> Crop / Soil Knowledge
  -> Rotation Engine
  -> Scenario Stress Testing
  -> Rotation Comparison
  -> Evidence-based Explanation
```

Every arrow is an explicit, typed data contract (see `docs/03_API_CONTRACT.md`). No stage may
silently mutate the output of the previous stage.

## 3. Architectural rules (non-negotiable)

1. **The scientific / modeling layer must NOT depend on an LLM.**
   The core engine runs entirely on deterministic calculations and documented assumptions.
   Given identical inputs it produces bit-identical outputs. It works offline. It is unit-testable.
2. **The LLM is only an explanation layer.** It converts structured model results (JSON) into
   human-readable language. It has no write access to any numeric field, cannot add facts, and
   its output is always accompanied by the structured payload it was derived from.
3. **Never invent scientific data.** Every coefficient must have a citation or be explicitly
   labelled as a placeholder awaiting calibration.
4. **Never invent NASA datasets or API values.** Only datasets listed in
   `docs/05_DATA_SOURCES_AND_PROVENANCE.md` may be referenced, and only for the purposes stated.
5. **Keep all data sources documented**, including retrieval date, spatial/temporal resolution,
   units, and licence.
6. **Clearly distinguish the four data classes** (see section 4). This distinction must survive
   all the way to the UI.
7. **Build an MVP first.** No feature ships unless it serves the core question above.
8. **Modules stay small and testable.** One responsibility per module; every module in
   `backend/engine/` ships with its own test file.

## 4. The four data classes

| Class | Meaning | Examples | Must be labelled in UI |
|---|---|---|---|
| **OBSERVED** | Directly measured / published by a data provider | MODIS NDVI time series, soil texture % from SSURGO, precipitation from Daymet | Yes + source card |
| **DERIVED** | Deterministic transformation of observed data | Annual heat-sum above base temperature, dry-spell length, water-supply index | Yes + formula shown |
| **ASSUMPTION** | Documented modelling choice, not measured | Rooting depth per crop, stress-sensitivity weights, N-fixation credit | Yes + rationale + sensitivity range |
| **SIMULATED** | Counterfactual produced by the Scenario Engine | "+2 °C warming", "-20 % growing-season rainfall" | Yes + "scenario, not a forecast" banner |

Rule: a value's class is stored alongside the value (`provenance.class`), never inferred.

## 5. Honesty constraints

- Output is a **relative comparison between candidate rotations under stated assumptions** —
  never a yield prediction, never agronomic advice, never a recommendation to plant.
- Confidence is reported explicitly (`confidence.level` = low/medium/high) and degrades when
  required inputs are missing or out of the calibrated domain.
- Any input outside the validated domain raises a warning that is surfaced in the UI, not swallowed.
- If the data needed for a dimension is unavailable, that dimension is marked
  `not_computed` rather than defaulted to zero or guessed.

## 6. Scope guard (MVP vs later)

**In scope for MVP:** farm profile (polygon or point + area), climate-normal + anomaly
environmental profile, curated crop-knowledge table, rule-based rotation generation,
deterministic multi-criteria scoring, scenario stress testing, robustness ranking,
comparison UI, map + time-series visualisation, optional LLM narrative.

**Explicitly out of scope for MVP:** process-based crop growth models, remote-sensing image
classification, ML yield prediction, market/price optimisation, irrigation scheduling,
multi-field whole-farm optimisation, user accounts, mobile app.

Adding anything from the out-of-scope list requires a written justification against the core
question. Do not add unnecessary features.

## 7. Repository etiquette

- Inspect before writing. Never overwrite existing work without asking.
- Small, reviewable commits; each phase ends with a green test suite.
- `docs/` is the source of truth for contracts. Code that diverges from `docs/` is a bug.
