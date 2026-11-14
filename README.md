# INGRES — National Groundwater Intelligence Platform
### AI-Assisted Hydrogeological Discovery, Verified Evidence Retrieval & Resource Sustainability Analytics

---

## 🚀 Live deployment

| | |
|---|---|
| **Console** | <https://ingres-console.vercel.app> |
| **Repository** | <https://github.com/ShelasAL/ingres-console> |
| **Hosting** | Vercel — Python runtime, `server.py` entrypoint, DuckDB file inside the function bundle |

The deployment runs the ask-in-plain-English console: Starlette API + the no-build UI over the DuckDB record.

**Bring your own key.** Open **Model settings** in the console and paste an OpenRouter / Gemini / OpenAI / custom-endpoint key. It stays in your browser's `localStorage` and travels only with your own questions. The deployment holds no API key, so without one it answers with the deterministic offline synthesizer (same numbers, plainer prose).

Redeploy after a change:

```powershell
npx vercel deploy --prod --yes
```

Not deployed: the legacy Streamlit app (`app/`, port 8501). Streamlit needs a long-running process with websockets, which a serverless function cannot provide — it stays a local tool. Deployment details: [docs/FRAMEWORK.md](docs/FRAMEWORK.md).

---

## 🌊 Overview & Problem Statement

### 🎯 The Problem
Groundwater is India's most critical yet invisible lifeline—accounting for **over 60% of irrigated agriculture and 85% of rural drinking water**. However, exploring and analyzing national groundwater data has traditionally suffered from three fundamental bottlenecks:
1. **Siloed & Massive Datasets**: Millions of readings across disparate formats (manual quarterly hydrographs, telemetry Digital Water Level Recorders [DWLR], and chemical laboratory tests) distributed across Central Ground Water Board (CGWB) and National Water Informatics Centre (NWIC) portals.
2. **AI Hallucinations in Scientific Queries**: Generic Large Language Models fabricate numbers, invent non-existent wells, hallucinate trends, and fail to distinguish actual physical measurements from plausible-sounding approximations.
3. **Lack of Provenance & Boundary Awareness**: Standard search engines fail to alert decision-makers when historical data is incomplete (e.g., date gaps, missing contaminants like Arsenic or Fluoride) or when a location is ambiguous.

### 💡 The Solution: INGRES Enterprise
**INGRES** is an enterprise-grade AI-assisted groundwater discovery system integrating **structured relational analytics (DuckDB)**, **deterministic Text-to-SQL**, **pre-answer coverage guardrails**, and **grounded natural language synthesis**. 

The system guarantees **100% cited provenance** (every number links back to official station IDs, dates, and quality flags), **zero fabricated values**, and **seamless multi-provider AI flexibility** (OpenRouter, Google Gemini, OpenAI, or local offline synthesis).

---

## 🏛️ Ingested Real-World Datasets

INGRES is backed by official real-world groundwater data directly streamed and synchronized from the **Ministry of Jal Shakti / CGWB National Water Data Portal** (`nwdp.nwic.gov.in`):

| State | Live CGWB Stations | Water Level Time-Series | Chemical Quality Tests | Key Hydrogeological Characteristics |
|---|---|---|---|---|
| **Rajasthan** | 304 | 1,465 | 1,500 | Arid, deep water tables (15–40+ mbgl), over-exploited blocks |
| **Punjab** | 441 | 1,496 | 1,500 | Intensive tubewell irrigation, severe stage of extraction |
| **Andhra Pradesh** | 336 | 1,498 | 1,480 | Granite hard-rock aquifers, endemic Fluoride challenges |
| **Delhi (NCT)** | 215 | 591 | 1,169 | Urban groundwater stress, saline pocket intrusion |
| **Kerala** | 243 | 1,500 | 1,500 | Coastal and midland laterite aquifers, high seasonal recharge |
| **Tamil Nadu** | 333 | 1,498 | 1,499 | Coastal salinity, hard-rock basalt & crystalline formations |
| **Uttar Pradesh** | 549 | 1,495 | 1,500 | Gangetic alluvium, high recharge, deep multi-aquifer systems |
| **Bihar** | 420 | 1,460 | 1,500 | Alluvial floodplains, historical arsenic contamination belt |
| **Total Database** | **3,042 Stations** | **16,780 Observations** | **11,978 Lab Samples** | **100 GEC-2015 Assessment Units** |

---

## 🚀 Key Features & Architectural Highlights

### 1. Zero-Hallucination Deterministic Retrieval
- **Read-Only AST Validation**: Ensures no state-altering SQL (`DROP`, `DELETE`, `UPDATE`, `INSERT`) can ever execute.
- **Resource Protection**: Automatically injects `LIMIT 500` to prevent memory saturation.
- **Multi-Table Normalization**: Normalized tables for `wells` (metadata), `gw_levels` (seasonal observations), `gw_quality` (chemical assays), and `assessment_units` (GEC-2015 block classifications).

### 2. Active Coverage & Boundary Detector
Before generating any answer, an automated rule engine intercepts queries:
- **Temporal Bounds**: Intercepts requests for unmonitored years (< 2015 or in the future) and flags `OUT_OF_SCOPE`.
- **Spatial Ambiguity**: Rejects vague locations (*"near the river"*, *"drought region"*, *"north India"*) with an `INSUFFICIENT` flag and guides the user to specific administrative units.
- **Data Gap Notification**: Explicitly quantifies available vs. missing readings (e.g., *"3 of 12 stations lack post-monsoon 2023 readings"*).

### 3. BIS 10500:2012 Water Quality Compliance Engine
Automated laboratory potability evaluation against Indian drinking water standards:
- **Fluoride**: $\le 1.0\text{ mg/L}$ (Acceptable) / $1.5\text{ mg/L}$ (Max Permissible)
- **TDS**: $\le 500\text{ mg/L}$ (Acceptable) / $2000\text{ mg/L}$ (Max Permissible)
- **Arsenic**: $\le 10\ \mu\text{g/L}$ (BIS / WHO Limit)
- **Nitrate**: $\le 45\text{ mg/L}$
- **pH**: $6.5 - 8.5$

### 4. Multi-Provider LLM & Zero-Key Offline Synthesis
- **Primary Provider**: **OpenRouter** (`https://openrouter.ai/api/v1`) using `meta-llama/llama-3.3-70b-instruct` or any open-source/proprietary model.
- **Fallback Spaces**: Google Gemini (`gemini-1.5-flash`), OpenAI (`gpt-4o-mini`), or local self-hosted endpoints (Ollama, LMStudio, vLLM).
- **Deterministic Hydro Synthesizer**: **No API key? No problem!** The system includes a built-in deterministic synthesizer that dynamically generates rich, accurate answers and hydrographs offline with zero external dependencies.

---

## 🖥️ Platform Modules Walkthrough

The application is structured into five cohesive modules:

### 1. `main.py` — Executive Command Center
- **National Metrics Bar**: Active monitoring stations, total observations, BIS compliance rate, and over-exploited basin counter.
- **State-wise Extraction Intensity**: Interactive visualization highlighting states exceeding the 100% GEC critical threshold.
- **Water Contamination Watch**: Real-time breakdown of High TDS, Fluoride exceedances, and Arsenic alerts.

### 2. `01_Groundwater_Copilot.py` — Scientific AI Assistant
- Natural language query assistant supporting conversational groundwater research.
- **Chronological Plotly Hydrographs**: Clean depth-to-water table lines grouped by station ID (no tangled zig-zags).
- **Dynamic Evidence Drawer**: View exact station citations, measurement dates, and data quality flags.
- **CSV Data Export**: 1-click download of retrieved evidence with guaranteed unique keys.
- **Human-in-the-Loop Flagging**: Escalate conflicting observations or data anomalies for expert review.

### 3. `02_Station_Dossier.py` — Well Telemetry & Health Inspector
- **Individual Station Search**: Select any of the **2,842 live CGWB stations** across 8 states.
- **Telemetry Health Score**: Percentage of validated records with `'good'` data flags.
- **Multi-Year Depth Hydrograph**: Interactive time-series with seasonal markers (`pre_monsoon`, `post_monsoon`, `rabi`, `kharif`).
- **Water Quality Radar**: Compares station's chemical samples against BIS drinking water limits.
- **Borehole Profile**: Depth, aquifer formation (alluvial, basalt, granite), and installation specifications.

### 4. `03_Data_Explorer.py` — Hydro Spatial Catalog
- Filter and search raw tabular data across all 4 database tables.
- Filter by State, District, Season, Data Quality Flag, and Potability status.
- Geographical station distribution maps and histogram distributions.

### 5. `04_Performance_Report.py` — Model Reliability & SLA Audit
- Comprehensive system SLAs:
  - **Deterministic SQL Success Rate**: 83.3%
  - **Zero-Hallucination Provenance Precision**: 100.0%
  - **Average Latency**: 32–86 ms (P95: 128 ms)
- Latency and accuracy breakdowns by query category.
- **Interactive Live Audit Runner**: Click a single button to execute all 30 benchmark test cases live.

### 6. `05_NWIC_Live_Sync.py` — In-App NWIC Data Synchronizer
- Live connection indicator for `nwdp.nwic.gov.in`.
- 1-click synchronization of state-level datasets directly into DuckDB with progress bars.

---

## ⚙️ Installation & Local Setup

### Prerequisites
- **Python**: Version 3.10, 3.11, or 3.12+
- **Git** (optional)

### 1. Clone & Setup Environment
```bash
# Clone the repository (or navigate to workspace)
cd c:\Users\shela\Downloads\csep

# Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` (optional — works 100% offline even without keys):
```ini
# Primary Provider: openrouter | gemini | openai | custom
LLM_PROVIDER=openrouter

# OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=meta-llama/llama-3.3-70b-instruct
LLM_BASE_URL=https://openrouter.ai/api/v1

# Optional fallback keys (can also be entered directly in the web UI sidebar)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Seed / Generate Initial Database
```bash
# Ingest official NWIC data for target states:
python ingest_all_target_states.py
```

### 5. Launch the Platform
```bash
streamlit run app/main.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🧪 Testing & Verification

Run the full automated test suite:
```bash
# Run 25 unit tests
pytest tests/ -v

# Run the 30-case benchmark evaluation
python run_evaluation.py
```

---

## ☁️ Deployment Guide

### Option 1: Streamlit Community Cloud (Free & 1-Click)
1. Push your repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub repository:
   - **Repository**: `your-username/ingres-groundwater`
   - **Branch**: `main`
   - **Main file path**: `app/main.py`
4. Under **Advanced Settings > Secrets**, add your optional API keys:
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-..."
   LLM_PROVIDER = "openrouter"
   ```
5. Click **Deploy!**

### Option 2: Docker Container Deployment
Create a `Dockerfile` in the root directory:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Seed DuckDB database
RUN python ingest_all_target_states.py

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run with Docker:
```bash
docker build -t ingres-platform .
docker run -p 8501:8501 -e OPENROUTER_API_KEY="your-key" ingres-platform
```

### Option 3: Production Cloud VM (AWS EC2 / Google Cloud Compute Engine)
```bash
# 1. Update server & install python
sudo apt update && sudo apt install -y python3-pip python3-venv git

# 2. Clone repository & install dependencies
git clone <repo-url> ingres && cd ingres
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python ingest_all_target_states.py

# 3. Setup systemd service for persistent 24/7 uptime
sudo nano /etc/systemd/system/ingres.service
```
Paste the following service definition:
```ini
[Unit]
Description=INGRES Groundwater Intelligence Platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ingres
ExecStart=/home/ubuntu/ingres/venv/bin/streamlit run app/main.py --server.port 80 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```
Start and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ingres
```

---

## 📁 Repository Directory Structure

```
csep/
├── data/                               # Data storage & pipeline scripts
│   ├── synthetic/
│   │   ├── generate_synthetic.py       # Baseline GEC generator
│   │   └── ingres.duckdb               # Master DuckDB database (3,042 stations)
│   └── geospatial/                     # Boundary GeoJSONs
├── ingres/                             # Core Python Intelligence Package
│   ├── data/
│   │   └── nwic_loader.py              # Official NWIC CKAN streamed downloader & parser
│   ├── schema/
│   │   ├── models.py                   # Pydantic v2 hydrogeology data schemas
│   │   └── db_setup.py                 # DuckDB DDL and connection handlers
│   ├── retrieval/
│   │   ├── query_router.py             # Intent classifier & entity extractor
│   │   ├── text_to_sql.py              # Safe read-only DuckDB SQL generation
│   │   ├── coverage_detector.py        # Pre-answer gap & ambiguity rules
│   │   ├── vector_search.py            # Hydrogeological semantic search (CGWB/GEC rules)
│   │   └── geo_filter.py               # Administrative boundary & coordinate resolution
│   ├── generation/
│   │   ├── llm_client.py               # Multi-provider client (OpenRouter, Gemini, OpenAI, Offline)
│   │   ├── context_assembler.py        # Context aggregation & statistical calculation
│   │   └── response_generator.py       # 6 scientific response states & evidence formatter
│   └── evaluation/
│       ├── baseline.py                 # Keyword baseline
│       └── metrics.py                  # Provenance precision, recall, and SLA metrics
├── app/                                # Streamlit Enterprise Interface
│   ├── main.py                         # Executive Command Center Dashboard
│   ├── components/
│   │   ├── provider_settings.py        # Model selector & API key fallback drawer
│   │   ├── provenance_card.py          # Evidence card with CSV export & review flag
│   │   ├── confidence_badge.py         # Visual confidence & response state badges
│   │   └── chat_interface.py           # Conversational container
│   └── pages/
│       ├── 01_Groundwater_Copilot.py   # AI Assistant with sorted hydrographs
│       ├── 02_Station_Dossier.py       # Comprehensive well profile & sensor health
│       ├── 03_Data_Explorer.py         # Multi-table hydro catalog with filters
│       ├── 04_Performance_Report.py    # System SLAs & live benchmark audit
│       └── 05_NWIC_Live_Sync.py        # In-app 1-click live CGWB data sync
├── tests/                              # Automated Test Suite (25 unit tests)
│   ├── fixtures/test_cases.json        # 30 documented benchmark queries
│   ├── test_schema.py
│   ├── test_text_to_sql.py
│   ├── test_coverage_detector.py
│   ├── test_response_generator.py
│   └── test_nwic_loader.py
├── docs/                               # Technical Documentation
│   ├── data_schema.md                  # Comprehensive relational schema
│   ├── assumptions.md                  # Scientific standards & acceptance criteria
│   └── evaluation_report.md            # Benchmark SLA audit report
├── ingest_all_target_states.py         # 1-click real CGWB ingestion script
├── run_evaluation.py                   # Reproducible 30-case benchmark runner
├── requirements.txt                    # Python dependencies
├── .env.example                        # Config template
└── README.md                           # Master Documentation
```

---

## 🏆 How We Address the Core Challenges

| Requirement | Conventional AI Approach | INGRES Implementation |
|---|---|---|
| **Data Representation** | Unstructured text documents chunked into vector DBs. | **Normalized Relational Store (DuckDB)**: Wells, seasonal levels, laboratory water quality, and GEC-2015 units. |
| **Scientific Querying** | Generic LLM attempts math and estimates depths. | **Deterministic Text-to-SQL**: Generates read-only analytical SQL with aggregation and window functions. |
| **Incomplete & Missing Data** | LLM hallucinates values to fill missing periods. | **Pre-Answer Coverage Guard**: Identifies temporal out-of-bounds, unmonitored parameters, and sparse station density. |
| **Data Provenance** | None; answers lack source references. | **100% Provenance Precision**: Explicit station IDs, observation dates, and data quality flags on every factual claim. |
| **Potability & Standards** | Subjective assessment. | **BIS 10500:2012 Engine**: Exact threshold testing for Fluoride, TDS, Arsenic, Nitrate, and pH. |
| **Accountability & Trust** | Black-box output. | **6 Response States**: Fully Supported, Partially Supported, Inferred, Insufficient Data, Out of Scope, and Human Review. |

---

## 📄 License & Attribution
- **Data Source**: Official groundwater telemetry and monitoring data provided by the Central Ground Water Board (CGWB) via the [National Water Data Portal](https://nwdp.nwic.gov.in/).
- **Evaluation Standards**: Ground Water Resource Estimation Committee (GEC-2015) & Bureau of Indian Standards (BIS 10500:2012).
