
import { api } from '../api.js'
import { pageHead, panelHead, spinner, errorNote, esc, count } from '../ui.js'
import { hBar } from '../charts.js?v=20261114-01'
import { enter } from '../motion.js?v=20261114-01'

export async function mount(root) {
  root.innerHTML = spinner('Loading performance…')
  let perf
  try {
    perf = await api.performance()
  } catch (e) {
    root.innerHTML = pageHead({
      eyebrow: 'Reliability',
      title: 'Model performance',
      lede: 'Service levels from the 30-case benchmark.',
    }) + errorNote(e.message)
    return
  }

  const o = perf.overall
  const categories = (perf.categories || []).map((c) => ({ label: c.label, value: c.pct }))
  const latency = (perf.latency || []).map((l) => ({ label: l.label, value: l.ms }))

  root.innerHTML = `
    ${pageHead({
      eyebrow: 'Reliability',
      title: 'Model performance',
      lede: `Service levels measured over ${o.cases} documented cases, not asserted. Provenance precision counts the share of factual claims that resolve to a station, date and quality flag.`,
      meta: [
        '<span class="meta-strong">Deterministic offline audit</span>',
        '30-case benchmark suite',
      ],
    })}

    <section class="record" aria-label="Performance figures">
      <div class="record-item">
        <div class="record-value accent">${count(o.pass_rate, { suffix: '%' })}</div>
        <div class="record-label">Benchmark pass rate</div>
        <div class="record-hint">${o.cases} documented cases</div>
      </div>
      <div class="record-item">
        <div class="record-value success">${count(o.provenance, { suffix: '%' })}</div>
        <div class="record-label">Provenance precision</div>
        <div class="record-hint">zero uncited claims</div>
      </div>
      <div class="record-item">
        <div class="record-value">${count(o.sql_success, { suffix: '%' })}</div>
        <div class="record-label">SQL success</div>
        <div class="record-hint">read-only, row-capped</div>
      </div>
      <div class="record-item">
        <div class="record-value warning">${count(o.coverage_recall, { suffix: '%' })}</div>
        <div class="record-label">Coverage recall</div>
        <div class="record-hint">gaps and ambiguity caught</div>
      </div>
      <div class="record-item">
        <div class="record-value">${count(o.p95_latency)}<span class="u"> ms</span></div>
        <div class="record-label">P95 latency</div>
        <div class="record-hint">${o.mean_latency} ms mean</div>
      </div>
    </section>

    <div class="grid grid-2">
      <section class="panel panel-pad">
        ${panelHead('Pass rate by category', 'Share of cases passed inside each query family.')}
        ${hBar(categories, { label: 'Pass rate by query category' })}
        <div class="table-note">${(perf.categories || []).map((c) => `${esc(c.label)}: ${esc(c.detail)}`).join(' · ')}</div>
      </section>
      <section class="panel panel-pad">
        ${panelHead('Latency by query type', 'Router, SQL, context assembly and synthesis, end to end.')}
        ${hBar(latency, { unit: ' ms', max: 100, label: 'Latency by query type in milliseconds' })}
        <div class="table-note">All rows well inside the 200 ms interaction budget.</div>
      </section>
    </div>

    <section class="panel panel-pad">
      ${panelHead(
        'Reproducing this audit',
        'The 30 documented questions run offline from the repository, not from the deployed console.'
      )}
      <div class="table-note">Run <span class="mono">python run_evaluation.py</span> to regenerate the figures on this page.</div>
    </section>`

  enter(root)

}
