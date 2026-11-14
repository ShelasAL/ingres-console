# INGRES — presenter script (10-minute demo)

SHOW = what to point at. The quote is what to say.

## Before you start

- App running at http://localhost:8501; keep dashboard and Copilot tabs open.
- Numbers: 3,042 stations · 16,780 water-level records · 11,978 lab tests · 100 GEC units.
- Backup: the deck screenshots. Do not debug in front of judges.
- Do not click Ingest Selected States during the demo.

## The three sentences

1. It answers from the database, not from the model.
2. Every number comes with a receipt: station, date and quality flag.
3. When the data cannot support an answer, it says so instead of guessing.

## Slide-by-slide

### Slide 1 · Title  [0:30]

**SHOW:** Title slide; stay on the wordmark.

> Groundwater is India’s invisible lifeline — most farming and most rural drinking water depends on it. But the answers are buried in millions of readings across government portals. INGRES makes that data answer questions a hydrogeologist can defend.

### Slide 2 · The problem  [0:45]

**SHOW:** Point at the three cards, then the four statistics.

> Three problems: data is siloed; generic AI invents numbers; answers do not say which station they came from. A confident wrong number is worse than no answer in water security.

### Slide 3 · Solution  [0:50]

**SHOW:** Point at the four pillars, then the number strip.

> We flipped the order: the database answers first, the AI only explains what it returned. Deterministic SQL, a coverage check, evidence on every claim, and freedom to use any model or none.

### Slide 4 · Dashboard  [0:40]

**SHOW:** KPIs, then bar chart, then donut.

> The national picture: 3,042 stations, 16,780 observations, 11,978 lab tests; extraction intensity against the 100% threshold; contamination watch. Pure aggregation, no model.

### Slide 5 · Architecture  [0:50]

**SHOW:** Trace left to right; then the data plane.

> Question to route to coverage to retrieval to assembly to generation to response. The data plane is DuckDB, a small knowledge base and live NWIC ingestion.

### Slide 6 · Query lifecycle  [0:50]

**SHOW:** Point at steps 2 and 7; let them read the SQL.

> Two steps matter most: coverage checked before answering, and evidence handed back at the end — rows, SQL, sources, expert-review option.

### Slide 7 · Data foundation  [0:35]

**SHOW:** Four table cards; standards chips.

> Four tables: stations, levels, quality, GEC units. Potability and GEC category are derived by rule, so every row is interpreted the same way.

### Slide 8 · Tech stack  [0:35]

**SHOW:** DuckDB, Streamlit, optional items.

> Small on purpose: Streamlit, single-file DuckDB, Plotly, Pydantic. The semantic stack and the model are optional — offline still works.

### Slide 9 · Copilot  [1:00]

**SHOW:** Provider badge, question, confidence badge, SQL.

> Live provider on the left; ask which state has the most potable wells; 399 wells, fully supported. The number cites the SQL result, and the evidence drawer has station IDs, dates and flags.

### Slide 10 · Dossier  [0:40]

**SHOW:** Filters, profile, map, hydrograph.

> Zoom into one well: aquifer, depth, coordinates, health score. The depth axis is reversed so a falling water table looks like a falling line.

### Slide 11 · Explorer  [0:35]

**SHOW:** Four tabs and the map.

> Anyone can verify the numbers themselves: filter the same four tables by state, season, flag, potability or GEC category.

### Slide 12 · Performance  [0:40]

**SHOW:** KPI row; two charts.

> Measured, not claimed: 83.3% SQL success, 100% provenance precision, edge cases intercepted. The button reruns the 30-case audit live.

### Slide 13 · Safety  [0:35]

**SHOW:** Four guardrails on the right.

> Read-only SQL, capped results, fixed BIS thresholds, and human review for conflicts. Refusal is the designed failure mode.

### Slide 14 · NWIC sync  [0:40]

**SHOW:** Status, selector, table, map.

> Official data streams from the national portal — 2,842 stations so far. Re-running updates instead of duplicating. If the portal is down, cached data still answers.

### Slide 15 · Evaluation  [0:45]

**SHOW:** Three cards, four bars; be honest about normal queries.

> 30 questions: 83.3% pass, 100% provenance, P95 38 ms. Edge cases and ambiguity pass completely; normal queries are the weak spot at 66.7% — we show it rather than hide it.

### Slide 16 · Run it  [0:30]

**SHOW:** Four terminal lines.

> Four commands, no API key required. A provider key improves the prose but not the retrieval, coverage or provenance.

### Slide 17 · Close  [0:30]

**SHOW:** Closing slide; slow down.

> Verified. Cited. Auditable. Not a chatbot that sounds right, but a system a hydrogeologist can defend.

## Numbers

| Metric | Value |
|---|---|
| Stations / observations / lab tests | 3,042  /  16,780  /  11,978 |
| GEC assessment units | 100  (8 over-exploited) |
| Potable samples | 91.7%  (997 non-potable) |
| Benchmark pass rate | 83.3%  (25 of 30) |
| Provenance precision | 100% |
| SQL success | 83.3% |
| Latency | 32 ms mean  ·  38 ms P95 |
| Unit tests | 25 passing |

## Likely questions

- **Why not just use ChatGPT?** — Because it invents numbers. We retrieve first and cite every value; the model only explains what the database returned.
- **Is the data real?** — Yes — official CGWB datasets streamed from the National Water Data Portal; 2,842 live stations in the current database.
- **What happens when data is missing?** — The coverage detector flags it before generation. The answer says what is missing and why, instead of filling the gap.
- **How accurate is it?** — 83.3% pass on 30 documented questions, with 100% provenance precision. We publish the weak spots too — normal queries are at 66.7%.
- **Why DuckDB?** — Single file, no server, full analytical SQL. It lets the whole platform ship as a repository plus one database file.
- **Does it need an API key?** — No. Without a key a deterministic synthesizer answers; with a key the narrative quality improves but the retrieval path does not change.
- **Can it scale?** — The retrieval is plain SQL, so it can move to a warehouse. The database is the bottleneck, not the interface.
- **What’s next?** — Tighten the fallback router, add more reviewed SQL templates, widen ingestion, and formalise the expert-review workflow.

## If something breaks

- App: restart with streamlit run app/main.py; health at http://localhost:8501/_stcore/health.
- Network: cached data still answers; NWIC shows limited access.
- Refusal: explain the coverage guardrail instead of apologising.
- Running long: drop slides 7, 8, 11, 16 — six-minute cut.

## Six-minute cut

Slides 1 → 2 → 3 → 4 → 9 (demo) → 13 → 15 → 17.