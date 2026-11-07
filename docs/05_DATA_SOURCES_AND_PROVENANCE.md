# FieldShift — Data Sources & Provenance (Phase 0)

> **Status of this document: CANDIDATE LIST, NOT YET VERIFIED.**
> Nothing below has been fetched or confirmed against a live API in this repository yet.
> Before Phase 2 code is written, every entry must be verified by a human running the actual
> endpoint/download and recording: exact product/short name, access URL, parameter names, units,
> spatial/temporal resolution, licence, and a sample response saved under `data_downloads/`.
> Any entry that cannot be verified is **removed**, not guessed. This satisfies rules 5–7 of
> `00_PROJECT_RULES.md` ("never invent NASA datasets or API values").

## 1. Registry schema (`backend/data/registry.py`)

```python
SourceRecord = {
  "source_id":        str,    # stable key used in Provenance.source_id
  "title":            str,
  "provider":         str,    # e.g. NASA, NOAA, USDA
  "product_or_dataset": str,  # EXACT short name as published — to be verified
  "purpose_in_app":   str,    # which indicator(s) it feeds; one row per use
  "spatial_resolution": str,
  "temporal_resolution": str,
  "units_as_published": str,
  "units_in_app":     str,
  "access_method":    "API | download | static file",
  "access_url":       str,    # verified URL
  "auth_required":    bool,   # e.g. Earthdata Login / EDL token
  "licence":          str,
  "citation":         str,
  "validated_domain": {"lat":[..], "lon":[..], "years":[..], "notes": str},
  "retrieval_policy": {"cache_ttl_days": int, "pin_retrieved_at": date|null},
  "verification":     {"status": "unverified|verified|failed",
                        "verified_by": str, "verified_on": date,
                        "sample_file": "data_downloads/..."}
}
```

CI rule: `assert all(p.source_id in SOURCE_REGISTRY for p in emitted_provenance)` and
`assert registry["verification"]["status"] == "verified"` for any source reachable from a
shipped demo path. Unverified sources may exist in the registry only behind a feature flag.

## 2. Candidate sources (to verify in Phase 2)

### A. Meteorology → daily temperature / precipitation (drives growing season, heat-sum, dry spells)
| source_id | Provider | Candidate product | Purpose | Verify |
|---|---|---|---|---|
| `NASA_POWER` | NASA POWER | daily point-metology product (temperature, precipitation) via its public API | OBSERVED daily met at farm center | ☐ |
| `DAYMET` | NASA ORNL DAAC | Daymet daily surface met (1 km) | alternative/cross-check gridded met | ☐ |
| `CLIMATE_NORMALS` | NOAA NCEI | 30-year climate normals | DERIVED anomaly baseline (explicit normal period) | ☐ |

Open questions to resolve during verification: exact parameter IDs and unit strings; whether an API
key/token is required; rate limits; missing-day semantics; timezone/date conventions; licensing text.

### B. Vegetation dynamics → NDVI/EVI time series (greenness, anomaly, phenology sanity check)
| source_id | Provider | Candidate product | Purpose | Verify |
|---|---|---|---|---|
| `MODIS_NDVI` | NASA LP DAAC | MODIS 16-day NDVI/EVI composite product (exact short name TBD) | OBSERVED greenness + anomaly vs normal years | ☐ |
| `LMODIS` or `VIIRS_NDVI` | NASA | higher-resolution NDVI alternative if needed | optional finer-resolution overlay | ☐ |
| Access route | NASA Worldview / CMR / Earthdata Search | how we programmatically obtain tiles or granules | retrieval mechanism | ☐ |

Verification must establish: native pixel size (and therefore honest AOI footprint reporting),
composite cadence, cloud/QA band semantics, and whether field-scale interpretation is defensible.

### C. Soils → local soil information
| source_id | Provider | Candidate product | Purpose | Verify |
|---|---|---|---|---|
| `SOIL_SSURGO` | USDA NRCS | SSURGO / gNATSO detailed soil survey (tabular + raster mirror) | texture, pH, organic carbon, water-holding, rooting-limiting depth | ☐ |
| `SOILGRIDS` | Soil Grids / ISRIC | global soil grids raster (fallback where SSURGO absent) | fallback attributes, lower confidence | ☐ |

Note for judges: coverage is national/regional dependent. Outside mapped areas the app returns
`not_computed`, and confidence drops — it does not substitute global data silently.

### D. Context / drought (optional, only if it earns its place)
| source_id | Provider | Candidate product | Purpose | Verify |
|---|---|---|---|---|
| `USDM` | USDA/NASA-linked drought monitor | periodic drought class | contextual banner on environmental panel | ☐ |

### E. Crop knowledge & assumptions (curated, cited — never invented)
Every row of `crop_traits.csv`, `rotation_rules.csv`, `stress_sensitivity.csv` needs a real citation
from an authoritative agronomy source chosen and recorded during Phase 4 (e.g. extension-service
crop guides, official variety/production handbooks such as *Crop Production Guide*-style references,
peer-reviewed rotation studies). Fields: `crop_id, trait, value/range, units, citation, retrieved_on,
assumption_rationale, sensitivity_range`. Rows lacking citations fail `scripts/validate_dataset.py`.

### F. Farm geometry inputs (user-supplied, not NASA)
User-drawn polygon, uploaded GeoJSON/shapefile, or a single lat/lon + area. Class = USER INPUT;
derived `area_ha` = DERIVED (method recorded: geodesic area via GeoPandas/Shapely CRS choice stated).

## 3. Scenario definitions (SIMULATED — explicitly counterfactual)

Scenarios are **parameterised perturbations of the observed profile**, not forecasts, and their
magnitudes come from a curated table with a documented rationale (each row cites the basis for the
range, e.g. published impact-study ranges or locally observed extreme-analogues):

| scenario_id | Perturbation (illustrative names/magnitudes — ranges to be justified in Phase 6) |
|---|---|
| `baseline` | identity (no delta) — used to prove pipeline consistency |
| `warm_plus1c` / `warm_plus2c` | shift mean/growing-season temperature by +1 / +2 °C |
| `dry_minus20_gs` | −20 % growing-season precipitation |
| `wet_spring_delay` | +N wet days before season start (delayed field operations proxy) |
| `late_frost` | frost event X days after modelled season start |
| `hot_spell_flowering` | k consecutive days above crop-specific threshold during reproductive window |
| `ndvi_decline_recent` | shift recent-years greenness anomaly downward |
| `priority_flip_*` | non-environmental stress: rotate farmer weights (soil-first ↔ water-first) |

Each scenario card in the UI states: what is changed, what is held fixed, why that magnitude, and
"is_simulated: true".

## 4. What we will NOT claim

- No claim that NDVI at ~250 m–1 km resolution measures *this field's* crops precisely; we report the
  pixel footprint and treat it as landscape-context evidence.
- No yield prediction, no economic forecast, no varietal recommendation.
- No causal attribution of anomalies to specific drivers without a cited source.
- No reanalysis/imputation presented as observation.

## 5. Verification checklist (gate to exit Phase 2)

- [ ] Each shipped `source_id` has `verification.status = verified`, a URL that resolves today, and a
      sample file committed under `data_downloads/` (or gitignored with hash recorded).
- [ ] Units confirmed from documentation, conversion formula written into `Provenance.formula`.
- [ ] Resolution + valid domain recorded; UI displays them next to every derived figure.
- [ ] Licence/attribution text captured for the submission package.
- [ ] Offline demo cache built for the demo region so judging needs no network.
- [ ] `docs/06_MODEL_ASSUMPTIONS.md` lists every ASSUMPTION-class constant with rationale.
