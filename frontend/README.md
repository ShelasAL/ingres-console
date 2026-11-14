# INGRES Console

The browser console for the groundwater pipeline: a Starlette API over a read-only DuckDB database, and a static UI with no build step.

- Live: <https://ingres-console.vercel.app>
- API and static host: Starlette and Uvicorn
- UI: plain ES modules, hand-written SVG charts
- Port: 8601

## Run

```powershell
python -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
```

Open `http://127.0.0.1:8601`.

On Vercel the same application is loaded through the root `server.py` entrypoint.

## Layout

```
frontend/
├── api/server.py          Starlette app: JSON API, query plans, static files
├── web/app/
│   ├── index.html
│   ├── styles.css
│   ├── data/india_states.geojson
│   └── js/
│       ├── app.js         shell, navigation, settings dialog
│       ├── api.js         fetch helpers, CSV export
│       ├── store.js       provider settings (localStorage)
│       ├── ui.js          badges, stats, small markdown renderer
│       ├── charts.js      SVG bar, donut and line charts
│       └── views/         dashboard, map, copilot, stations, explore, performance
└── screenshots/           captures of each page
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | service status, database path, static bundle, provider |
| GET | /api/summary | KPIs, extraction by state, contamination, potability, GEC categories |
| GET | /api/states | states with station counts |
| GET | /api/districts?state= | districts in a state |
| GET | /api/stations?district= | stations in a district |
| GET | /api/station/{well_id} | profile, levels, quality, district assessment |
| GET | /api/map/stations?state= | every station with coordinates |
| GET | /api/explore?table=&state= | wells, levels, quality or units, 200 rows |
| POST | /api/ask | route, coverage, SQL, answer |
| GET | /api/performance | recorded benchmark metrics and category breakdown |

## Design notes

The UI is plain ES modules loaded by the browser, so there is no bundler and nothing to install. The API layer would serve a React build unchanged if one were needed later.

Offline answers are planned, not templated: `_plan_query` resolves district and state names against the database, classifies the question, and runs a parameterized read-only query. `_deterministic_answer` then reports counts, min/mean/max, BIS exceedances, year-on-year change or a glossary definition.

The console is read-only. It cannot ingest or modify data, so a live demo cannot damage the record.

## Provider settings

Open **Model settings**. Choose Offline, OpenRouter, Gemini, OpenAI or a custom base URL. The key is stored in the browser's localStorage and sent with each question; the server does not keep it.

## Map

The Map page draws state boundaries and every station in SVG, with no tiles and no API key.

- Boundaries load from `web/app/data/india_states.geojson`, simplified from the udit-001/india-maps-data TopoJSON.
- The state filter highlights one state, dims the rest and zooms to it.
- Dot colour follows potability from each station's latest sample: potable, non-potable, marginal, no sample.
- Hover shows station ID, district and type; click opens the profile panel with aquifer, depth, coordinates and latest sample.

## Verified

- All five pages render without JavaScript exceptions.
- Explore returns 200 rows across four tables.
- Copilot returns a grounded answer with badge, evidence, SQL and a chart.
- Performance reports the recorded 30-case figures.
- Distinct questions return distinct answers, including refusals for places outside the database.
- The deployed build answers `/api/ask` in under 100 ms offline, and in about 9 s with a provider key.

## Known gaps

- The console is single-user and has no authentication layer.
- Data ingestion is not exposed in this UI.
- The first request after idle takes a few seconds on Vercel while the runtime starts.
