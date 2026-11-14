# INGRES Groundwater Assistant — Assumptions and Acceptance Criteria
## SIH 2026 — Problem Code SIH26063

### 1. Documented Assumptions

#### Temporal Coverage
- **Historical Monitoring Range**: The system indices groundwater monitoring records from **2015 to 2023**.
- Queries targeting years prior to 2015 or post-2023 are explicitly classified by the **Coverage Detector** as `OUT_OF_SCOPE`. No predictive extrapolation or fabricated historical data is generated.

#### Spatial Coverage
- Station coordinates are strictly constrained within mainland India's geographic bounds (`6.0°N to 38.0°N`, `68.0°E to 98.0°E`).
- Vague regional references (e.g., *"North India"*, *"near the river"*, *"drought region"*) are rejected with an `INSUFFICIENT` coverage status, requesting specific district or state clarification.

#### Measurement Standards & Units
- Depth to water table is expressed in **metres below ground level (mbgl)**. Higher numbers denote deeper water tables / declining aquifer heads.
- Groundwater resource volumes are measured in **Million Cubic Metres (MCM)**.
- Water quality thresholds strictly adhere to **BIS 10500:2012** specifications.

#### Safety and Read-Only Execution
- The SQL engine strictly enforces read-only `SELECT` queries.
- Any generated query containing keywords such as `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, or `TRUNCATE` is terminated immediately before execution.
- All executed SQL queries automatically append a `LIMIT 500` clause to guard against memory exhaustion.

---

### 2. Documented Acceptance Criteria

| Component | Test Criteria | Acceptance Threshold |
|---|---|---|
| **Data Layer (CO5)** | Station metadata, levels, quality, and assessments validated with Pydantic | 100% valid schema types, FK referential integrity passing |
| **Coverage Detector (CO5)** | Intercept out-of-bounds dates, vague locations, and missing parameters | ≥ 60% detection recall across 30 benchmark queries |
| **SQL Engine (CO5)** | Executable, error-free DuckDB SQL queries without syntax or schema violations | ≥ 80% SQL execution success rate |
| **Provenance Integrity (CO6)** | Every factual response includes stations (`well_id`), dates, and quality flags | 100% provenance precision with zero unsupported fabrications |
| **Interface Accountability (CO6)**| Color-coded confidence badges, 6 distinct response states, and human-review flags | Rendered across all queries in conversational Streamlit UI |
| **Reproducibility** | Full suite execution via automated scripts | Single-command reproduction (`py -3 run_evaluation.py`) |

