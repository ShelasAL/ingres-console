# INGRES

A groundwater question-answering console for India. You ask in plain English; the answer is built from a database of CGWB and NWIC station records, and every number carries its station, date and standard.

- **Live console:** <https://ingres-console.vercel.app>
- **Repository:** <https://github.com/ShelasAL/ingres-console>
- **Problem:** SIH 2026, problem code SIH26063
- **Team:** Shelas, Adithya

## What it does

The database answers first. A language model only rewrites what the database returned, so it cannot add a number that was never measured.

- Accepts questions about water levels, water quality, extraction, wells and aquifers.
- Cites the rows behind each answer: station IDs, sample dates, quality flags and the executed SQL.
- Checks coverage before answering, and refuses when the record cannot support the question.
- Works with no API key, using a deterministic answer built from the same rows.

## How it works

1. **Understand.** The question is matched to an intent and a place (state or district).
2. **Retrieve.** A reviewed, parameterized SQL query reads the DuckDB database.
3. **Check.** A coverage detector decides whether the data supports the question.
4. **Explain.** Totals, BIS exceedance lists and comparison facts are precomputed; the model writes the prose.
5. **Show.** The answer returns with a summary, evidence, SQL, sources and a confidence level.

If a model writes a station ID that is not in the retrieved rows, the answer falls back to the plain database result.

## The data

One DuckDB file, `data/synthetic/ingres.duckdb`, holds:

| Table | Rows | Contents |
|---|---|---|
| `wells` | 3,042 | Monitoring stations, 12 states and 257 districts |
| `gw_levels` | 16,780 | Water-table depth readings from 2015 to 2025 |
| `gw_quality` | 11,978 | Lab samples with BIS 10500 parameters and potability |
| `assessment_units` | 100 | GEC-2015 extraction assessment per block |

Potability and GEC categories are derived by rule in the schema, so the same threshold applies to every row. Limits used: fluoride 1.5 mg/L, TDS 500 mg/L, nitrate 45 mg/L, arsenic 10 µg/L.

## Stack and why

| Technology | Why |
|---|---|
| DuckDB | One file, no server, read-only analytical SQL over the whole record in milliseconds |
| Starlette + Uvicorn | A small JSON API that also serves the static console |
| Plain ES modules, hand-written SVG | No build step, no framework, nothing to reinstall |
| Pydantic | Typed schema for ingestion |
| Any LLM, or none | OpenRouter, Gemini, OpenAI or a custom endpoint; the offline synthesizer needs no key |
| Vercel | Serverless Python hosting; the database and UI ship inside the function |

## Run locally

Requires Python 3.12 or newer.

```powershell
pip install -r requirements.txt
python -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
```

Open `http://127.0.0.1:8601`.

An API key is optional. Without one, answers come from the deterministic synthesizer. With one, open **Model settings** in the console and paste the key; it is stored in your browser and sent only with your own questions.

## Test

```powershell
python -m pytest -q
```

69 tests cover query plans, place matching, coverage, evidence formatting and provider handling.

A 30-case evaluation (`python run_evaluation.py`) reports 83.3% pass rate, 100% provenance precision, 32 ms mean latency and 38 ms at P95.

## Project layout

```
frontend/api/server.py     API, query plans, answer assembly
frontend/web/app/          Console UI (plain ES modules)
ingres/retrieval/          Coverage detector, query router, SQL execution, knowledge search
ingres/generation/         Evidence assembly, prompt, LLM client
ingres/schema/             DuckDB schema and Pydantic models
data/synthetic/            The database file
tests/                     Unit and integration tests
server.py                  Vercel entrypoint
```

## Limits

- 12 states and 257 districts are indexed; this is not the whole country.
- Quality sampling is uneven, and some districts have very few lab results.
- The first request after idle takes a few seconds on Vercel while the runtime starts.

## Docs

- `docs/FRAMEWORK.md`: how the system is built, file by file
- `docs/FRAMEWORK.md#8-deployment-vercel`: deployment notes
- `docs/presentation/INGRES_Project_Deck_Canva.pptx`: project presentation
