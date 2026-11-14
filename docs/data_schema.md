# INGRES Data Schema Documentation
## SIH 2026 — Problem Code SIH26063

The INGRES Groundwater Assistant operates over a relational, normalized data representation aligned with the **Central Ground Water Board (CGWB)** and **India-WRIS** monitoring standards.

---

### 1. Table: `wells` (Station Metadata)
Stores location, aquifer characteristics, and borehole configuration.

| Field | Type | Description |
|---|---|---|
| `well_id` | `VARCHAR PRIMARY KEY` | Unique station code, e.g., `GW_RJ_JAI_001` |
| `state` | `VARCHAR NOT NULL` | State or Union Territory |
| `district` | `VARCHAR NOT NULL` | District name |
| `block` | `VARCHAR` | Block/Taluk name |
| `latitude` | `DOUBLE` | Decimal degrees (bounds: 6.0 to 38.0 N) |
| `longitude` | `DOUBLE` | Decimal degrees (bounds: 68.0 to 98.0 E) |
| `well_type` | `VARCHAR` | `open_well`, `piezometer`, `borewell`, `dug_well` |
| `aquifer_type` | `VARCHAR` | `unconfined`, `confined`, `semi-confined` |
| `depth_mbgl` | `DOUBLE` | Total borehole depth (metres below ground level) |
| `installation_year`| `INTEGER` | Year of installation |
| `data_source` | `VARCHAR` | Source identifier (`CGWB-NWIC`) |

---

### 2. Table: `gw_levels` (Temporal Measurements)
Stores seasonal and quarterly water table level records.

| Field | Type | Description |
|---|---|---|
| `record_id` | `VARCHAR PRIMARY KEY` | Unique measurement identifier |
| `well_id` | `VARCHAR REFERENCES wells` | Foreign key to `wells` |
| `measurement_date` | `DATE NOT NULL` | Date of reading |
| `season` | `VARCHAR` | `pre_monsoon`, `post_monsoon`, `rabi`, `kharif` |
| `depth_to_water_mbgl` | `DOUBLE` | Depth to water table in mbgl (higher = deeper) |
| `water_level_mbsl` | `DOUBLE` | Water level relative to mean sea level |
| `measurement_method` | `VARCHAR` | `manual`, `telemetry`, `estimated` |
| `data_quality_flag` | `VARCHAR` | `good`, `suspect`, `missing`, `estimated` |
| `remarks` | `VARCHAR` | Hydrogeologist observations |

---

### 3. Table: `gw_quality` (Chemical Quality Parameters)
Stores laboratory chemical test results evaluated against **BIS 10500:2012**.

| Parameter | Column | Acceptable Limit | Maximum Permissible | Unit |
|---|---|---|---|---|
| pH | `ph` | 6.5 | 8.5 | — |
| Total Dissolved Solids | `tds_mg_l` | 500 | 2000 | mg/L |
| Fluoride | `fluoride_mg_l` | 1.0 | 1.5 | mg/L |
| Arsenic | `arsenic_ug_l` | 10 | 50 | µg/L |
| Nitrate | `nitrate_mg_l` | 45 | 45 | mg/L |
| Total Hardness | `hardness_mg_l` | 200 | 600 | mg/L |
| Iron | `iron_mg_l` | 0.3 | 0.3 | mg/L |
| Potability Status | `potability` | — | — | `potable`, `non_potable`, `marginal`, `unknown` |

---

### 4. Table: `assessment_units` (GEC-2015 Resource Estimation)
Dynamic groundwater assessment metrics calculated at assessment unit (block/taluk) level.

| Field | Type | Description |
|---|---|---|
| `unit_id` | `VARCHAR PRIMARY KEY` | Assessment unit code |
| `annual_gw_recharge_mcm` | `DOUBLE` | Annual replenishable recharge (MCM) |
| `extractable_gw_mcm` | `DOUBLE` | Total extractable groundwater resource (MCM) |
| `total_extraction_mcm` | `DOUBLE` | Annual draft for irrigation, domestic & industrial (MCM) |
| `stage_of_extraction_pct`| `DOUBLE` | Ratio: `(total_extraction / extractable) * 100` |
| `category` | `VARCHAR` | `safe` (<70%), `semi_critical` (70-90%), `critical` (90-100%), `over_exploited` (>100%), `saline` |
| `assessment_year` | `INTEGER` | Year of assessment (e.g. 2020, 2022) |
| `methodology` | `VARCHAR` | Standard methodology (`GEC-2015`) |

