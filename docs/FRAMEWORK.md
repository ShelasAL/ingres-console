# INGRES — How the Framework Is Built

This is a short, practical guide to how the app is put together: what technology is used and why, what is in the database, how the folders are laid out, and the lines of code that matter.

INGRES is an ask-in-plain-English assistant over India's groundwater record. **The database answers first; a language model only rewrites the answer.** That is the single idea that shapes everything else.

---

## 1. The flow of every question

```
Question (typed in the browser)
   │
   ▼
frontend/api/server.py      → understands the question (intent + place)
   │
   ▼
coverage_detector.py        → is there data for that place and period?
   │
   ▼
DuckDB (read-only)          → parameterized SQL fetches the rows
   │
   ▼
context_assembler.py        → numbers, totals, BIS exceedances are precomputed
   │
   ▼
llm_client.py / response_generator.py  → model writes the answer
   │
   ▼
server.py                   → summary, answer, evidence, SQL, sources, confidence
   │
   ▼
frontend/web/app            → rendered with a supported/unsupported badge
```

Nothing is invented. If the record cannot support the question, the answer says so and says why.

---

## 2. Why DuckDB — and how it is used

**Why DuckDB**

| Reason | What it means here |
|---|---|
| One file, no server | The whole database is `data/synthetic/ingres.duckdb` (~9 MB). No database administration, no ports. |
| Columnar + fast | Aggregations (means, counts, exceedances) run in milliseconds. |
| Full SQL | Filters, joins, window functions, `GROUP BY` — everything the reviewed query plans need. |
| Read-only mode | The app opens it read-only, so no answer can ever damage the record. |
| Ships with the repo | Anyone who clones the project and has Python can run the whole app. |

**How it is used**

```python
# frontend/api/server.py:33
def db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)
```

- `DB_PATH` comes from the `DB_PATH` environment variable or defaults to `data/synthetic/ingres.duckdb`.
- The app never writes to it. Ingestion (`ingest_all_target_states.py`) creates it separately via `ingres/schema/db_setup.py`.

**What it includes** (live counts):

| Table | Rows | What it holds |
|---|---|---|
| `wells` | 3,042 | One row per monitoring station — state, district, coords, aquifer type |
| `gw_levels` | 16,780 | Water-table depth in mbgl per visit, seasonal |
| `gw_quality` | 11,978 | pH, TDS, nitrate, fluoride, arsenic, iron, hardness, potability |
| `assessment_units` | 100 | GEC-2015 extraction assessment per block (stage of extraction %, recharge MCM, category) |

Schema in `ingres/schema/db_setup.py` (excerpt):

```sql
CREATE TABLE IF NOT EXISTS gw_levels (
    record_id           VARCHAR PRIMARY KEY,
    well_id             VARCHAR NOT NULL REFERENCES wells(well_id),
    measurement_date    DATE   NOT NULL,
    depth_to_water_mbgl DOUBLE,
    ...
);
```

The demo database models the CGWB / NWIC record; BIS 10500 and GEC-2015 classifications are derived **by rule** in the schema, not by hand.

---

## 3. Other technologies and why they are used

### Starlette + Uvicorn — the API
A tiny, standard Python web layer (not Flask pulling in Werkzeug/Jinja, not Django). It does three things: answers JSON questions at `/api/...`, serves the static console, runs the app on one port.
```python
# frontend/api/server.py — bottom of the file
app = Starlette(routes=[Route("/api/ask", ask, methods=["POST"]), ...])
```
`run_in_threadpool` wraps the DB work so a slow query never blocks the event loop (`frontend/api/server.py`).

### Plain ES modules — the UI
No build step, no framework, no `node_modules`. npm was unreachable in the build environment, and the result is a handful of readable files anyone can audit:
- `frontend/web/app/index.html` — the shell; loads `js/app.js` as a module with a cache-busting `?v=20261112-01`.
- `js/views/*.js` — one file per screen (dashboard, map, copilot, stations, explore, performance).
- `js/charts.js` — SVG charts drawn by hand (bars, lines, donut) without D3.
- `js/theme.js`, `js/store.js` — theme preference and the saved provider settings (`ingres-settings` in `localStorage`).
- `js/api.js` — the only place that knows the API paths (`/api/ask`, `/api/summary`, ...).

Dark + light themes, mobile-friendly layout, `prefers-reduced-motion` respected.

### LLM — optional, swappable, with an offline fallback
`ingres/generation/llm_client.py` talks to OpenRouter, Gemini, OpenAI, or any custom endpoint (the demo uses NVIDIA's). If no key is configured, answers still come back from a deterministic synthesizer — plainer, but still grounded and correct.
Key points:
- `DEFAULT_OPENROUTER_MODEL` can be overridden per request;
- `reasoning.enabled=false` is sent by default so reasoning models don't burn the token budget, with a retry if the gateway rejects it;
- **the model never sees a raw SQL result set — it sees a compact evidence packet** (`_format_evidence` in `response_generator.py`) and a list of precomputed statistics, so it cannot miscompute a total.

### Pydantic — type-checked schema
`ingres/schema/models.py` (e.g. `WellMetadata`) normalizes and bounds-checks every row during ingestion — coordinates inside India, `depth_mbgl >= 0`, year limits, etc.

### Loguru + pytest + a coverage detector
`loguru` for structured server logs, `pytest` (66 tests in `tests/`), and `coverage_detector.py` for a pre-answer check: does this state/district/year have data, or is this question out of scope?

### Streamlit (legacy UI)
`app/` is the original Streamlit dashboard, still working on port **8501**. The console at **8601** is the primary interface now; they share the same database and `ingres/` pipeline.

---

## 4. File structure and what each part does

```
├── README.md                 Project framing & headline numbers
├── run.txt                   How to start the console (8601)
├── requirements.txt          Runtime dependencies (console + Vercel)
├── ingest_all_target_states.py  One-off ingestion of the source record
├── run_evaluation.py         Reruns the 30-case benchmark
│
├── ingres/                   Core Python package (shared by both apps)
│   ├── schema/db_setup.py    DuckDB schema (CREATE TABLE statements)
│   ├── schema/models.py      Pydantic models used at ingestion time
│   ├── retrieval/
│   │   ├── coverage_detector.py  Pre-answer check: FULL / PARTIAL / INSUFFICIENT / OUT_OF_SCOPE
│   │   ├── text_to_sql.py        LLM-based SQL planner with validation + LIMIT guard
│   │   ├── query_router.py       Routes free-text questions to reviewed intents
│   │   ├── geo_filter.py         State/district filters
│   │   └── vector_search.py      Knowledge-base retrieval (aquifer concepts, etc.)
│   ├── generation/
│   │   ├── context_assembler.py  Builds the evidence packet for the model
│   │   ├── llm_client.py         Multi-provider client + offline synthesizer
│   │   └── response_generator.py Prompt, section parsing, Evidence list
│   └── evaluation/metrics.py   Benchmark metrics (SQL success, provenance, latency)
│
├── frontend/
│   ├── api/server.py          The whole API in one file — routing, plans, answer logic
│   ├── web/app/               The console UI (plain ES modules, hand-written SVG)
│   └── capture_console.mjs    Headless-Edge screenshot helper (console previews)
│
├── app/                       Legacy Streamlit UI (port 8501)
├── data/synthetic/ingres.duckdb   The DuckDB file — the entire record, one ~9 MB database
├── tests/                     66 unit/integration tests
├── docs/                      Schema, assumptions, evaluation report, prompts, this file
└── docs/presentation/         Decks, planner scripts, PNG previews
```

---

Deployment-only files at the root: `server.py` (Vercel entrypoint), `vercel.json` (duration + bundled assets), `.vercelignore` (what is not uploaded), `requirements-streamlit.txt` (the legacy stack, not installed on Vercel) and `.python-version`.

---

## 5. The important lines, file by file

Line numbers point into `frontend/api/server.py` unless noted otherwise.

### `frontend/api/server.py` — the hub

| Line | What it is / why it matters |
|---|---|
| 33 | `duckdb.connect(DB_PATH, read_only=True)` — the whole safety story in one line. |
| 502–508 | Intent regexes: `ASSESS_RE` (extraction), `QUALITY_RE` (chemistry), `NON_POTABLE_RE`, `LEVEL_RE` — the console understands questions without a router model first. |
| 528 | `_match_location()` — longest district/state inside the question; matches `uttarpradesh` against `Uttar Pradesh` (compact comparison). |
| 636 | `_unknown_location()` — refuses Paris / `jaipr` / "West Bengal" instead of answering from national data. Answers must never be about the wrong place. |
| 675 | `_plan_query()` — reviewed, parameterized SQL plans: quality/level comparisons, non-potable lists, potability counts, well counts, over-exploited districts. |
| 833 | Counts branch: potability questions come back with wells, chemistry and the reason ("2 of 4 wells non-potable, TDS 540.5 above the 500 limit"). |
| 990 | `run_pipeline()` — the orchestrator: coverage → SQL → stats → model → guards → final JSON. |
| 973 / 1074 | Guard: if the model paraphrased a refusal, the reason is appended *once*, not twice. |
| 968 / 1080 | Guard: a well ID that does not exist in the retrieved rows forces a fallback to the grounded answer (`WELL_ID_RE` + `_unknown_well_ids`, line 965). |
| 1162 | `ask()` — endpoint behind the Copilot's Ask button. |
| 1257–1268 | Routes: `/api/summary`, `/api/states`, `/api/stations`, `/api/map/stations`, `/api/ask`, ... |

The JSON every endpoint returns is deliberately shaped like the UI needs it — no framework, no DTO classes, just `{state, confidence, summary, answer, evidence, sql, sources, ...}`.

### `ingres/schema/db_setup.py:8` — `SCHEMA_SQL`
The four tables and the `FOREIGN KEY` from levels/quality to stations. One source of truth for ingestion and tests.

### `ingres/retrieval/coverage_detector.py:218` — `check_coverage(query, entities, con)`
Before anything is generated: does the mentioned state/district have levels, quality, or assessment rows, and in what years? Returns a `CoverageResult` with `status` in `{FULL, PARTIAL, INSUFFICIENT, OUT_OF_SCOPE}`. Constants like `MIN_YEAR = 2015` gate questions the record cannot support.

### `ingres/generation/context_assembler.py:154` — `assemble_context(...)`
Builds the packet the model sees:
- `_compute_stats()` (line 41) precomputes totals (`total_wells`, `total_non_potable_wells`, `total_potable_wells`), `potable_pct`, `bis_violations`, `bis_exceedances` (well_id-level lists for fluoride >1.5, TDS >500, nitrate >45, arsenic >10 µg/L), `potability_summary`.
- **This is why the model rarely miscomputes:** the stats are facts, not suggestions.

### `ingres/generation/response_generator.py:278` — `generate_response(...)`
Trains the model on a fixed brief:
- "Answer ONLY from the evidence below. Never invent values."
- "Use any `total_*` statistic verbatim as the total."
- "Only call a well over a limit when `bis_exceedances` lists it."
- "Copy well_id values character for character."
- Output format: `**Summary** / **Answer** / **Evidence** / **Coverage Note** / **Confidence** / **Recommendation**.`
- `**Summary**` is parsed into a separate `resp.summary` shown above the answer in the UI.

### `ingres/generation/llm_client.py` — `LLMClient`
OpenRouter by default, Gemini, OpenAI, or a custom base URL (used with NVIDIA NIM at `https://integrate.api.nvidia.com/v1` in the demo). Auto-retries once without the thinking switch if the gateway rejects it, raises the token budget if the model spends everything reasoning, and falls back to the deterministic synthesizer if the provider errors.

### `frontend/web/app/js/store.js`
`ingres-settings` in `localStorage` decides provider/model/key. Switching the demo between providers needs no rebuild — the page reads it at startup.

### `frontend/web/app/js/views/copilot.js` and `js/charts.js`
Renders badges (coverage, confidence, intent), the model summary above the answer, the evidence drawer, and inline SVG charts for level trends and exceedance bars.

---

## 6. Why it is built this way — the short version

| Choice | Because |
|---|---|
| Database answers first, model second | A confident wrong number is worse than no answer. |
| Read-only DuckDB | No destructive blast radius. |
| Reviewed SQL plans, not free-form text-to-SQL | Parameters are bound; injection cannot happen. |
| Precomputed stats & BIS lists | Arithmetic does not depend on the model. |
| Refusal as a designed output | Missing data is reported, not papered over. |
| Model is a swappable part | Any endpoint — or none — still answers. |
| No framework, no build step | The code stays small enough to read and defend. |

---

## 7. How to run it

```powershell
cd "/d C:\Users\shela\Downloads\csep - Copy"
"%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
```

Open `http://127.0.0.1:8601`. Demo questions: see `docs/presentation/INGRES_Demo_Deck.pptx` and the demo flow notes.

**Tests:** `& "$env:LOCALAPPDATA\Python\pythoncore-3.15-64\python.exe" -m pytest -q` (66 passing).

---

## 8. Deployment (Vercel)

| | |
|---|---|
| Console | <https://ingres-console.vercel.app> |
| Repository | <https://github.com/ShelasAL/ingres-console> |
| Runtime | Vercel Python 3.12, ASGI app loaded from `server.py` |

**How it is wired**

- `server.py` (repo root) puts the project root on `sys.path` and re-exports `app` from `frontend/api/server.py`. Vercel's Python runtime only looks for `app`/`application` in `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py`.
- `vercel.json` pins the function's `maxDuration` to 60 s and bundles the two runtime assets via `includeFiles`: `data/synthetic/**` (the 9 MB DuckDB file) and `frontend/web/app/**` (the UI).
- `requirements.txt` is the lean runtime set (duckdb, starlette, uvicorn, pandas, numpy, scikit-learn, pydantic, requests, loguru). The heavy Streamlit / ChromaDB / torch stack lives in `requirements-streamlit.txt` and is not installed on Vercel.
- `.python-version` = `3.12`.
- `.vercelignore` drops `app/`, `.streamlit/`, `tests/`, `docs/` and the deck binaries from the upload. **Paths are anchored with a leading `/`** — a bare `app` entry also matched `frontend/web/app`, which silently removed the UI from the function bundle.
- The API opens DuckDB with `read_only=True`, so the function never writes to its bundled file; each request opens a fresh in-memory connection over the 9 MB file.

**Bring your own key (BYOK).** No API key is set on the deployment (`/api/health` reports `key_present: false`). Each user pastes a provider key in **Model settings**; `localStorage` keeps it and every `/api/ask` call carries it. Without a key the deterministic synthesizer answers from the same retrieved rows.

**Redeploy**

```powershell
npx vercel deploy --prod --yes            # from the repo root, after `vercel login`
```

**Known limits on Vercel**

- Cold start ~2–3 s (imports duckdb + pandas); the first question after idle is slower.
- Static files are served by the Python function, not the CDN — fine for a demo, but a `public/` split would be faster under load.
- The 30-case audit runs locally (`python run_evaluation.py`, about two minutes); it is not exposed as an endpoint because it would exceed the function limit.
- The Streamlit UI in `app/` cannot run here (long-lived process + websockets). It remains a local tool on port 8501.
