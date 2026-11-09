# FieldShift — Data Sources & Provenance (Phase 0)

> **Status: NASA POWER has partial API verification; its source record remains unverified.**
> A successful sample JSON response was observed during read-only research, but parameter-specific
> spatial resolution, historical coverage, licence terms, and request limits were not established.
> The provider implementation is not wired to a shipped demo path. Do not treat the synthetic test
> fixture as source evidence or treat NASA POWER values as field measurements.

## 1. Registry record (`backend/data/registry.py`)

```python
SourceRecord(
  source_id, title, provider, product_or_dataset, source_type, purpose_in_app,
  access_url, access_method, authentication_required,
  temporal_resolution, parameters, units_by_parameter,
  spatial_resolution, historical_coverage, validated_domain, licence,
  citation, cache_ttl_days, verification_status, verification_notes
)
```

`source_type` distinguishes where the source data come from (for example, provider-supplied grid
data) and is separate from the application's four data classes. For NASA POWER, provenance uses
`source_type="PROVIDER_GRIDDED"`; this is not a farm weather-station observation and does not
establish field-scale conditions. Unknown or unverified facts are `None`; they are not inferred from
generic product descriptions. The cache TTL is the default policy, and a provider instance may
override it.

CI rule: `assert all(p.source_id in SOURCE_REGISTRY for p in emitted_provenance)` and
`assert registry["verification"]["status"] == "verified"` for any source reachable from a
shipped demo path. Unverified sources may exist in the registry only behind a feature flag.

## 1.1 Curated agronomy evidence registry (`backend/data/agronomy_registry.py`)

The agronomy evidence registry is separate from `backend/data/registry.py`, which describes
retrievable environmental-data providers such as NASA POWER. The agronomy registry loads
version-controlled CSV records from `backend/data/curated/` and does not fetch sources or store
provider observations.

Each curated claim includes a source ID, exact page/table/section locator, geographic scope,
production-system scope (`IRRIGATED`, `RAINFED`, or `UNKNOWN`), evidence kind, evidence status,
time applicability, and any stated reference period. `VERIFIED` means that the claim and locator
were checked against the cited source. It does **not** establish current applicability, farm-level
validity, or a recommendation.

The registry's `evidence_kind` values (`PUBLISHED_STATISTIC` and
`PUBLISHED_DESCRIPTIVE_CLAIM`) describe the form of a cited claim; they are not additions to the
four application data classes in `backend/schemas/common.py`. Historical district/block aggregates
are published statistics, not direct observations from an individual farm. Keep their geographic
and temporal scope attached, and do not infer farm soil, irrigation access, or crop history from
them. Unknown calendar dates remain blank and carry `window_status="UNKNOWN"`.

The initial Madurai records cite the TNAU Madurai District Agriculture Plan (2017–18), the Madurai
District Agriculture Department page, and the TNAU KVK Madurai Major Crops page. The KVK page is
undated; its time applicability is therefore `UNKNOWN`. Soil survey categories and irrigation
statistics are not crop traits and must not be encoded as crop traits or used as farm-level values.

## 2. Candidate sources (to verify in Phase 2)

### A. Meteorology → daily temperature / precipitation (drives growing season, heat-sum, dry spells)
| source_id | Provider | Candidate product | Purpose | Verify |
|---|---|---|---|---|
| `NASA_POWER` | NASA POWER | POWER Daily Point API | Provider-supplied daily gridded meteorology for regional context | Partial; see §2.1 |
| `DAYMET` | NASA ORNL DAAC | Daymet daily surface met (1 km) | alternative/cross-check gridded met | ☐ |
| `CLIMATE_NORMALS` | NOAA NCEI | 30-year climate normals | DERIVED anomaly baseline (explicit normal period) | ☐ |

Open questions to resolve during verification: effective spatial resolution, complete historical
coverage, licence and attribution text, authentication policy, rate limits, and full missing-day
semantics.

### 2.1 NASA POWER Daily Point API — partial verification

- **Official documentation:** [Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).
- **Endpoint:** `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Request configuration used for research:** community `AG`; format `JSON`; time standard `UTC`;
  parameters `PRECTOTCORR`, `T2M_MAX`, and `T2M_MIN`.
- **Response metadata observed:** all requested parameters were present; `PRECTOTCORR` reported
  `mm/day`; `T2M_MAX` and `T2M_MIN` reported `C`; the fill value was `-999.0`; and the time
  standard was `UTC`. The response included source metadata. A sample request returned JSON, but an
  HTTP status code was not captured.
- **Authentication:** the observed request was made without credentials. Authentication policy has
  not been independently documented here.
- **Not verified:** effective spatial resolution for each parameter, full historical coverage,
  licensing/attribution terms, request limits, and rate-limit policy. Do not substitute generic
  endpoint wording such as “native resolution” for a parameter-specific resolution.
- **Geographic caveat:** the prior illustrative Madurai city-centre request is not a farm location.
  Production coordinates must be supplied from a farm profile; district or city-centre data must
  not be represented as field observations. Provider output uses
  `source_type="PROVIDER_GRIDDED"`; NASA POWER grid-cell data are not direct farm-station
  measurements.

  The provider's `PROVIDER_GRIDDED` source type is present in the data-layer result and registry.
  Propagation into API-schema provenance is deferred until API integration; existing API schemas
  remain unchanged in Phase 2B.
- **Missing data:** the API fill value `-999.0` and absent daily values are preserved as missing
  (`null`) by the provider. No interpolation or imputation is performed.
- **Fixture:** `backend/tests/fixtures/nasa_power_daily.json` is explicitly synthetic test input;
  it is not a captured NASA response and does not satisfy the source-sample verification gate.

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
The implemented Madurai evidence registry currently loads `agronomy_sources.csv`, `crop_traits.csv`,
and `crop_calendars.csv` from `backend/data/curated/`. Source rows record
`source_id, provider, title, publication_year, version, url, accessed_date, geographic_scope,
source_kind, verification_status, time_applicability, notes`. Claim rows in `crop_traits.csv`
record `record_id, crop_id, crop_name, claim, value, unit, source_id, source_locator,
geographic_scope, production_system_scope, evidence_kind, evidence_status, time_applicability,
reference_period, notes`. Calendar rows use those claim fields plus `season, activity, window_start,
window_end, window_status, timing_note`.

Each claim's `source_id` links it to one source record; `source_locator` identifies the exact cited
page, table, or section. `evidence_kind` describes whether the claim is a published statistic or a
published descriptive claim. A source's `verification_status` applies to that source record, while
`evidence_status` records verification of the individual claim and locator against the source. A
`VERIFIED` claim must reference a source marked `VERIFIED`; neither status establishes current
applicability or farm-level validity. These evidence fields do not change the application
`DataClass` enum. Unknown calendar dates remain blank and explicitly marked `UNKNOWN`. No
rotation-rules dataset is currently implemented.

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
      real sample file committed under `data_downloads/` (or gitignored with hash recorded).
- [ ] Units confirmed from documentation, conversion formula written into `Provenance.formula`.
- [ ] Resolution + valid domain recorded; UI displays them next to every derived figure.
- [ ] Licence/attribution text captured for the submission package.
- [ ] Offline demo cache built for the demo region so judging needs no network.
- [ ] `docs/06_MODEL_ASSUMPTIONS.md` lists every ASSUMPTION-class constant with rationale.
