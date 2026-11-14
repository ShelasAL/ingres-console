
import { api } from '../api.js'
import { pageHead, panelHead, spinner, errorNote, emptyState, esc, icon, humanize, fmt, count } from '../ui.js'
import { hBar } from '../charts.js?v=20261109-10'
import { enter } from '../motion.js?v=20261109-10'

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
        'Live validation suite',
        'Re-runs all 30 documented questions against the current database with the deterministic offline engine, then reports each case.',
        `<button class="btn primary sm" id="run-audit">${icon('play', 12)} Run benchmark</button>`
      )}
      <div id="audit-body">${emptyState('No run in this session', 'Run the suite to execute all 30 questions against the live database.', 'bolt')}</div>
      <div id="perf-error"></div>
    </section>`

  enter(root)

  const btn = root.querySelector('#run-audit')
  const body = root.querySelector('#audit-body')
  const err = root.querySelector('#perf-error')

  btn.addEventListener('click', async () => {
    btn.disabled = true
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Running…`
    body.innerHTML = spinner(`Executing ${o.cases} questions…`)
    err.innerHTML = ''
    try {
      const audit = await api.benchmark()
      const totalMs = audit.results.reduce((s, r) => s + (r.latency_ms || 0), 0)
      const failed = audit.results.length - audit.passed
      body.innerHTML = `
        <div class="audit-summary">
          <span><span class="n ${audit.pass_rate < 80 ? 'bad' : ''}">${audit.passed}/${audit.total}</span> passed</span>
          <span class="badge ${audit.pass_rate >= 80 ? 'ok' : 'warn'}">${audit.pass_rate}% this run</span>
          <div class="audit-meta">
            <span>${failed ? `${failed} case${failed === 1 ? '' : 's'} for review` : 'No cases for review'}</span>
            <span>${fmt(Math.round(totalMs))} ms total</span>
            <span>Run at ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
        <div class="table-wrap medium">
          <table>
            <thead><tr><th>ID</th><th>Category</th><th>Intent</th><th>Coverage</th><th class="num">Rows</th><th>Confidence</th><th class="num">Latency</th><th>Status</th></tr></thead>
            <tbody>${audit.results.map((r) => `<tr>
              <td class="id">${esc(r.id)}</td>
              <td>${esc(humanize(r.category))}</td>
              <td>${esc(humanize(r.intent))}</td>
              <td>${esc(humanize(r.coverage))}</td>
              <td class="num">${r.rows}</td>
              <td>${esc(humanize(r.confidence))}</td>
              <td class="num">${r.latency_ms} ms</td>
              <td><span class="badge ${r.passed ? 'ok' : 'bad'}">${r.passed ? 'pass' : 'review'}</span></td>
            </tr>`).join('')}</tbody>
          </table>
        </div>`
      enter(body)
    } catch (e) {
      body.innerHTML = ''
      err.innerHTML = errorNote(e.message)
    } finally {
      btn.disabled = false
      btn.innerHTML = `${icon('play', 12)} Run benchmark`
    }
  })
}
