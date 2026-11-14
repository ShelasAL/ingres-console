# INGRES Console — alternative frontend

A second user interface over the same groundwater pipeline and DuckDB database.
The Streamlit application is untouched and still runs on port 8501.

- **API + static host:** Starlette / Uvicorn (no extra Python packages)
- **UI:** dependency-free ES modules, hand-written SVG charts (no build step)
- **Port:** 8601

## Run

```powershell
# from the repository root
& "$env:LOCALAPPDATA\Python\pythoncore-3.15-64\python.exe" -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
# open http://127.0.0.1:8601
```

If `python` is not on PATH, use the interpreter that already runs the project:

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.15-64\python.exe" -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
```

The Streamlit app remains separate:

```powershell
streamlit run app/main.py        # http://localhost:8501
```

## Why no React build

An initial React + Vite version was written, but the npm registry is effectively
unreachable from Node in this environment (a 1 MB download timed out after
200 s). Rather than ship an unbuildable source tree, the console is plain ES
modules loaded by the browser — no bundler, no node_modules, no build step.
The API layer is unchanged and can serve a React build later.

## Layout

```
frontend/
├── api/server.py          Starlette app: JSON API + static files
├── web/app/
│   ├── index.html
│   ├── styles.css
│   └── js/
│       ├── app.js         shell, navigation, settings modal
│       ├── api.js         fetch helpers, CSV export
│       ├── store.js       provider settings (localStorage)
│       ├── ui.js          badges, stats, markdown-ish renderer
│       ├── charts.js      SVG bar / donut / line charts
│       └── views/         dashboard, map, copilot, stations, explore, performance
├── screenshots/           live captures of each page
└── capture_console.mjs    headless-Edge capture script (dev tool)
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | service status, DB path, provider |
| GET | /api/summary | KPIs, extraction by state, contamination, potability, GEC categories |
| GET | /api/states | states with station counts |
| GET | /api/districts?state= | districts in a state |
| GET | /api/stations?district= | stations in a district |
| GET | /api/station/{well_id} | profile, levels, quality, district assessment |
| GET | /api/map/stations?state= | every station with coordinates (optionally one state) |
| GET | /api/explore?table=&state= | wells / levels / quality / units (200 rows) |
| POST | /api/ask | full pipeline: route → coverage → SQL/vector → answer |
| GET | /api/performance | benchmark metrics and category breakdown |
| POST | /api/benchmark | runs the 30-case suite (deterministic offline engine) |

## Parity with Streamlit

The console reuses the existing modules — `query_router`, `coverage_detector`,
`text_to_sql`, `context_assembler`, `response_generator` — against a read-only
DuckDB connection. Response states, confidence levels, coverage notes, evidence
rows and executed SQL are the same objects the Streamlit UI renders.

Two deliberate differences:

1. **Offline answers.** With no provider key the Streamlit app calls the shared
   offline synthesizer, which answers every question with the same generic
   water-quality paragraph. The console instead plans the query itself
   (`_plan_query`): it resolves district/state names against the database,
   detects quality / level / trend / assessment intent, and runs a
   parameterized read-only query. `_deterministic_answer` then reports counts,
   min/mean/max, BIS exceedances, year-on-year change or a glossary definition.
   With a key, both use the same router, Text-to-SQL and `generate_response`.
2. **Read-only surface.** The console has no NWIC ingestion button; it reads the
   database only, so a demo cannot mutate data.

## Provider settings

Sidebar → **Model settings**. Choose Offline / OpenRouter / Gemini / OpenAI /
custom base URL. The key is stored in the browser's localStorage and sent with
each question; it is never persisted server-side.

## Verified

- all five pages render with no JavaScript exceptions
- explore returns 200 rows across four tables
- copilot returns a grounded answer with badge, evidence, SQL and bar chart
- benchmark endpoint: 24 / 30 passed in 1.7 s
- typed questions submit with Enter or the Ask button; the input renders white
  on the dark theme
- distinct questions return distinct answers (levels, trends, quality,
  over-exploited units, state potability ranking, definitions)
- map renders 35 state boundaries and 3,042 stations at 1.25 px radius
  (1,693 potable, 313 non-potable, 1,036 without a sample); the state filter
  narrows to 325 for Rajasthan, highlights that state and zooms to it; zoom
  controls change the viewBox; clicking a dot opens the profile panel and
  "Open full dossier" lands on that station with the profile already loaded
- screenshots captured at 1600 px wide

## Known gaps

- The online-provider path was not exercised (no API key in this environment).
- The console is single-user and local; there is no auth layer.
- NWIC ingestion and CSV-of-session-answers are not exposed in this UI.
## Map

The Map page draws India's state boundaries plus every station, entirely in SVG —
no tiles, no API key, works offline.

- **Boundaries:** `web/app/data/india_states.geojson` — 35 states/UTs,
  4,755 points, 88 KB, simplified from the
  [udit-001/india-maps-data](https://github.com/udit-001/india-maps-data)
  TopoJSON.
- **State filter** (top right) highlights the chosen state, dims the rest and
  zooms to its bounding box; "All states" resets.
- **Zoom / pan:** scroll to zoom at the cursor, drag to pan, the + / − / ⌂
  buttons, or double-click to reset.
- **Dot colour** encodes potability from each station's latest laboratory sample:
  potable (green), non-potable (red), marginal (amber), no sample (grey).
  A thin white ring marks a suspect or estimated level reading.
- **Hover** shows station ID, district and type; **click** opens the profile
  panel with aquifer, depth, coordinates, readings and latest sample.
- **Open full dossier** carries the selection to the Stations page.
