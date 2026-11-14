
import { api } from '../api.js'
import { pageHead, panelHead, skeleton, errorNote, fmt, esc, count } from '../ui.js'
import { hBar, donut, miniBars } from '../charts.js?v=20261109-10'
import { enter } from '../motion.js?v=20261109-10'

export async function mount(root) {
  root.innerHTML = skeleton()
  let d, states
  try {
    ;[d, states] = await Promise.all([api.summary(), api.states()])
  } catch (e) {
    root.innerHTML = pageHead({
      eyebrow: 'National posture',
      title: 'National groundwater posture',
      lede: 'The indexed CGWB / NWIC monitoring record.',
    }) + errorNote(e.message)
    return
  }

  const k = d.kpi
  const stateCount = states.length
  const potable = (d.potability || []).find((p) => p.potability === 'potable') || { n: 0 }
  const non = (d.potability || []).find((p) => p.potability === 'non_potable') || { n: 0 }
  const total = potable.n + non.n || 1
  const potableShare = Math.round((potable.n / total) * 1000) / 10

  const extraction = (d.states || []).slice(0, 10).map((s) => ({ label: s.state, value: s.stage }))
  const violations = [
    { label: 'High TDS', value: d.violations.tds || 0 },
    { label: 'Nitrate', value: d.violations.nitrate || 0 },
    { label: 'Fluoride', value: d.violations.fluoride || 0 },
    { label: 'Arsenic', value: d.violations.arsenic || 0 },
  ]
  const violationTotal = violations.reduce((s, v) => s + v.value, 0)

  const toneFor = (category) => {
    if (category === 'critical') return 'warn'
    if (category === 'over_exploited') return 'bad'
    return ''
  }
  const categories = (d.categories || []).map((c) => ({
    label: c.category.replace(/_/g, ' '),
    value: c.n,
    tone: toneFor(c.category),
  }))

  const sourceRows = d.sources || []
  const live = sourceRows.find((s) => /live/i.test(s.data_source))
  const baseline = sourceRows.find((s) => !/live/i.test(s.data_source))

  root.innerHTML = `
    ${pageHead({
      eyebrow: 'National posture',
      title: 'National groundwater posture',
      lede: `${fmt(k.stations)} monitoring stations, ${fmt(k.observations)} water-level readings and ${fmt(k.tests)} laboratory samples across ${stateCount} states — every figure aggregated straight from the indexed CGWB / NWIC record.`,
      meta: [
        '<span class="meta-strong">Read-only record</span>',
        'CGWB / NWIC · GEC-2015',
      ],
    })}

    <section class="record" aria-label="National figures">
      <div class="record-item">
        <div class="record-value">${count(k.stations)}</div>
        <div class="record-label">Monitoring stations</div>
        <div class="record-hint">${stateCount} states · geolocated wells</div>
      </div>
      <div class="record-item">
        <div class="record-value">${count(k.observations)}</div>
        <div class="record-label">Water-level readings</div>
        <div class="record-hint">seasonal telemetry</div>
      </div>
      <div class="record-item">
        <div class="record-value">${count(k.tests)}</div>
        <div class="record-label">Laboratory samples</div>
        <div class="record-hint">BIS 10500 parameters</div>
      </div>
      <div class="record-item">
        <div class="record-value success">${count(k.potable_pct, { suffix: '%' })}</div>
        <div class="record-label">Potable samples</div>
        <div class="record-hint">${fmt(non.n)} non-potable</div>
      </div>
      <div class="record-item">
        <div class="record-value danger">${count(k.over_exploited)}</div>
        <div class="record-label">Over-exploited units</div>
        <div class="record-hint">above 100% extraction</div>
      </div>
    </section>

    <div class="grid grid-3-2">
      <section class="panel panel-pad">
        ${panelHead(
          'Extraction intensity by state',
          'Average stage of extraction against the 100% GEC critical threshold. State averages stay below the line; 8 individual assessment units do not.',
          `<span class="chip">${esc(d.states[0] ? d.states[0].state + ' highest' : 'GEC-2015')}</span>`
        )}
        ${hBar(extraction, { threshold: 100, label: 'Average stage of extraction by state' })}
      </section>

      <section class="panel panel-pad">
        ${panelHead('Contamination watch', 'Samples above the BIS 10500 maximum for each parameter. One sample may count in more than one category.')}
        ${donut(violations, {
          label: 'exceedances',
          colors: ['var(--series-1)', 'var(--series-3)', 'var(--series-2)', 'var(--series-4)'],
        })}
        <div class="table-note">${fmt(violationTotal)} parameter exceedances across ${fmt(k.tests)} samples.</div>
      </section>
    </div>

    <div class="grid grid-2">
      <section class="panel panel-pad">
        ${panelHead('Drinking water potability', 'Samples inside all four BIS limits: TDS, fluoride, nitrate and arsenic.')}
        <div class="big-figure"><span class="n">${count(potableShare, { decimals: 1, suffix: '%' })}</span><span class="u">potable · ${fmt(potable.n)} of ${fmt(total)} samples</span></div>
        <div class="split-bar" role="img" aria-label="${potableShare}% potable, ${(100 - potableShare).toFixed(1)}% non-potable">
          <div class="split-fill" style="--target-width:${potableShare}%"></div>
        </div>
        <div class="split-legend">
          <span><i class="dot ok"></i> Potable <strong>${fmt(potable.n)}</strong></span>
          <span><i class="dot bad"></i> Non-potable <strong>${fmt(non.n)}</strong></span>
        </div>
      </section>

      <section class="panel panel-pad">
        ${panelHead('GEC-2015 assessment units', `${fmt(k.units)} block-level units classified by extraction and salinity.`)}
        ${miniBars(categories)}
        <div class="table-note">Categories follow Ground Water Resource Estimation Committee 2015.</div>
      </section>
    </div>

    <div class="method-strip" aria-label="Method and sources">
      <div class="method-item">
        <h3>Source</h3>
        <p>${live ? `<strong>${fmt(live.n)}</strong> stations from the live CGWB / NWIC sync` : 'CGWB / NWIC live sync'}${baseline ? `, <strong>${fmt(baseline.n)}</strong> from the baseline set` : ''}. Read-only access, no ingestion from this console.</p>
      </div>
      <div class="method-item">
        <h3>Standards</h3>
        <p>Potability against <strong>BIS 10500:2012</strong>; extraction categories against <strong>GEC-2015</strong>. Thresholds appear beside every quality figure.</p>
      </div>
      <div class="method-item">
        <h3>Retrieval</h3>
        <p>Queries run against DuckDB through a read-only, row-capped path. Every answer carries station IDs, dates and data-quality flags.</p>
      </div>
    </div>`

  root.querySelector('.page-head h1')?.classList.add('posture-title')
  enter(root)
}
