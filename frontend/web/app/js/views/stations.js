
import { api, downloadCsv } from '../api.js'
import { takePendingStation } from '../store.js'
import { pageHead, panelHead, spinner, errorNote, chip, esc, icon, humanize, fmt, dateOf, count } from '../ui.js'
import { line } from '../charts.js?v=20261109-10'
import { enter } from '../motion.js?v=20261109-10'

const LIMITS = [
  { key: 'ph', label: 'pH', min: 6.5, max: 8.5, limit: '6.5 – 8.5' },
  { key: 'tds_mg_l', label: 'TDS', max: 500, limit: '≤ 500 mg/L' },
  { key: 'fluoride_mg_l', label: 'Fluoride', max: 1.5, limit: '≤ 1.5 mg/L' },
  { key: 'nitrate_mg_l', label: 'Nitrate', max: 45, limit: '≤ 45 mg/L' },
  { key: 'arsenic_ug_l', label: 'Arsenic', max: 10, limit: '≤ 10 µg/L' },
  { key: 'hardness_mg_l', label: 'Hardness', max: 600, limit: '≤ 600 mg/L' },
]

function qualityStatus(item, value) {
  if (value === null || value === undefined) return { tone: 'muted', label: 'no value' }
  const n = Number(value)
  if (item.min !== undefined && n < item.min) return { tone: 'bad', label: 'below limit' }
  if (n > item.max) return { tone: 'bad', label: 'exceeds limit' }
  if (item.min !== undefined) return { tone: 'ok', label: 'within limit' }
  return n > item.max * 0.8 ? { tone: 'warn', label: 'near limit' } : { tone: 'ok', label: 'within limit' }
}

export async function mount(root) {
  root.innerHTML = `
    ${pageHead({
      eyebrow: 'Well telemetry',
      title: 'Station dossier',
      lede: 'Profile, telemetry health, hydrograph and chemistry for one monitoring station. Every quality figure is tested against its BIS 10500:2012 limit.',
    })}
    <div id="station-error"></div>
    <div class="panel filterbar" aria-label="Choose a station">
      <label class="field"><span>State</span><select id="f-state"></select></label>
      <label class="field"><span>District</span><select id="f-district"></select></label>
      <label class="field"><span>Station</span><select id="f-station"></select></label>
    </div>
    <div id="station-body">${spinner('Loading station…')}</div>`

  const err = root.querySelector('#station-error')
  const selState = root.querySelector('#f-state')
  const selDistrict = root.querySelector('#f-district')
  const selStation = root.querySelector('#f-station')
  const body = root.querySelector('#station-body')
  let detail = null
  const pending = takePendingStation()

  const options = (items, valueKey, labelKey) =>
    items.map((it) => `<option value="${esc(it[valueKey])}">${esc(it[labelKey])}</option>`).join('')

  async function loadDistricts(state, preferDistrict, preferWell) {
    const list = await api.districts(state)
    selDistrict.innerHTML = options(list, 'district', 'district')
    const chosen = preferDistrict && list.some((d) => d.district === preferDistrict)
      ? preferDistrict
      : (list[0] ? list[0].district : null)
    if (chosen) {
      selDistrict.value = chosen
      await loadStations(chosen, preferWell)
    }
  }

  async function loadStations(district, preferWell) {
    const list = await api.stations(district)
    selStation.innerHTML = options(list, 'well_id', 'well_id')
    const chosen = preferWell && list.some((s) => s.well_id === preferWell)
      ? preferWell
      : (list[0] ? list[0].well_id : null)
    if (chosen) {
      selStation.value = chosen
      await loadDetail(chosen)
    } else {
      body.innerHTML = `<div class="panel empty">No stations were returned for ${esc(district)}.</div>`
    }
  }

  async function loadDetail(wellId) {
    body.innerHTML = spinner('Loading station…')
    try {
      detail = await api.station(wellId)
      renderDetail()
    } catch (e) {
      body.innerHTML = errorNote(e.message)
    }
  }

  function renderDetail() {
    if (!detail) return
    const m = detail.meta
    const levels = detail.levels || []
    const quality = detail.quality || []
    const good = levels.filter((l) => l.data_quality_flag === 'good').length
    const health = levels.length ? Math.round((good / levels.length) * 1000) / 10 : 0
    const latest = levels.length ? levels[levels.length - 1] : null
    const latestQ = quality[0]
    const points = levels
      .filter((l) => l.depth_to_water_mbgl !== null)
      .map((l) => ({ x: l.measurement_date, y: l.depth_to_water_mbgl }))
    const assess = detail.assessment && detail.assessment[0]
    const assessTone = assess
      ? (Number(assess.stage_of_extraction_pct) > 100 ? 'bad' : Number(assess.stage_of_extraction_pct) > 90 ? 'warn' : 'ok')
      : 'ok'
    const assessClass = assessTone === 'bad' ? 'text-danger' : assessTone === 'warn' ? 'text-warn' : ''

    const qualityCards = latestQ
      ? LIMITS.map((item) => {
          const value = latestQ[item.key]
          const status = qualityStatus(item, value)
          return `<div class="quality-card">
            <div class="quality-label">${item.label}</div>
            <div class="quality-value ${status.tone === 'muted' ? '' : status.tone}">${value === null || value === undefined ? '—' : value}</div>
            <div class="quality-limit"><span class="dot ${status.tone}"></span><span>${status.tone === 'bad' ? 'exceeds' : item.limit}</span></div>
          </div>`
        }).join('')
      : ''

    body.innerHTML = `
      <section class="panel dossier-head">
        <div>
          <h2>${esc(m.well_id)}</h2>
          <p class="dossier-sub">${esc(m.district)}, ${esc(m.state)} · ${esc(humanize(m.block) || 'block not recorded')}</p>
          <div class="dossier-tags">
            ${chip(humanize(m.aquifer_type) || 'aquifer unknown')}
            ${chip(humanize(m.well_type) || 'well type unknown')}
            ${chip(m.data_source)}
            ${chip(m.installation_year ? 'installed ' + m.installation_year : 'installation unknown')}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          ${latestQ ? `<span class="badge ${latestQ.potability === 'potable' ? 'ok' : 'bad'}">${esc(humanize(latestQ.potability))}</span>` : '<span class="badge neutral">No laboratory sample</span>'}
          <span class="badge ${health > 80 ? 'ok' : health > 50 ? 'warn' : 'bad'}">${health}% good flags</span>
        </div>
      </section>

      <section class="record four" aria-label="Station figures">
        <div class="record-item">
          <div class="record-value">${count(levels.length)}</div>
          <div class="record-label">Historical readings</div>
          <div class="record-hint">${good} with a good flag</div>
        </div>
        <div class="record-item">
          <div class="record-value">${latest ? latest.depth_to_water_mbgl + '<span class="u"> m</span>' : '—'}</div>
          <div class="record-label">Latest depth</div>
          <div class="record-hint">metres below ground level</div>
        </div>
        <div class="record-item">
          <div class="record-value ${health > 80 ? 'success' : health > 50 ? 'warning' : 'danger'}">${count(health, { decimals: 1, suffix: '%' })}</div>
          <div class="record-label">Telemetry health</div>
          <div class="record-hint">readings with a good flag</div>
        </div>
        <div class="record-item">
          <div class="record-value">${latest ? dateOf(latest.measurement_date) : '—'}</div>
          <div class="record-label">Latest observation</div>
          <div class="record-hint">${latest ? esc(humanize(latest.season)) : 'no readings'}</div>
        </div>
      </section>

      <div class="grid grid-3-2">
        <section class="panel panel-pad">
          ${panelHead(
            'Water table',
            'Depth to water in metres below ground. Larger values sit lower on the chart.',
            `${points.length ? `<span class="chip">${points.length} readings</span>` : ''}<button class="btn sm ghost" id="download-levels" style="margin-left:8px">${icon('download', 13)} CSV</button>`
          )}
          ${points.length ? line(points, { height: 268 }) : '<div class="chart-empty">No depth readings for this station.</div>'}
        </section>

        <section class="panel panel-pad">
          ${panelHead('Station profile')}
          <dl class="profile">
            <div><dt>State</dt><dd>${esc(m.state)}</dd></div>
            <div><dt>District</dt><dd>${esc(m.district)}</dd></div>
            <div><dt>Block</dt><dd>${esc(m.block || '—')}</dd></div>
            <div><dt>Aquifer</dt><dd>${esc(humanize(m.aquifer_type) || '—')}</dd></div>
            <div><dt>Well type</dt><dd>${esc(humanize(m.well_type) || '—')}</dd></div>
            <div><dt>Borehole depth</dt><dd>${m.depth_mbgl === null ? '—' : m.depth_mbgl + ' mbgl'}</dd></div>
            <div><dt>Installed</dt><dd>${m.installation_year || '—'}</dd></div>
            <div><dt>Coordinates</dt><dd>${Number(m.latitude).toFixed(3)}, ${Number(m.longitude).toFixed(3)}</dd></div>
            <div><dt>Source</dt><dd>${esc(m.data_source)}</dd></div>
            <div><dt>Quality flag</dt><dd>${latest ? esc(humanize(latest.data_quality_flag)) : '—'}</dd></div>
          </dl>
          ${assess ? `<div class="assessment">
            <div class="assessment-head">District assessment · ${assess.assessment_year}</div>
            <div class="assessment-row"><span>Stage of extraction</span><strong class="${assessClass}">${assess.stage_of_extraction_pct}%</strong></div>
            <div class="assessment-row"><span>GEC category</span><strong>${esc(humanize(assess.category))}</strong></div>
            <div class="assessment-row"><span>Annual recharge</span><strong>${fmt(assess.annual_gw_recharge_mcm)} MCM</strong></div>
            <div class="assessment-row"><span>Extraction</span><strong>${fmt(assess.total_extraction_mcm)} MCM</strong></div>
          </div>` : ''}
        </section>
      </div>

      <section class="panel panel-pad">
        ${panelHead(
          'Chemical quality & potability',
          'Latest laboratory sample tested against BIS 10500:2012. Amber marks a value within 20% of its limit; red marks an exceedance.',
          latestQ ? `<span class="chip ${latestQ.potability === 'potable' ? 'ok' : 'bad'}">${esc(humanize(latestQ.potability))} · ${dateOf(latestQ.sample_date)}</span>` : ''
        )}
        ${latestQ ? `<div class="quality-cards">${qualityCards}</div>` : '<div class="empty">No chemical samples recorded for this station.</div>'}
        ${quality.length ? `<div class="table-wrap medium">
          <table>
            <thead><tr><th>Sample date</th><th class="num">pH</th><th class="num">TDS mg/L</th><th class="num">Fluoride mg/L</th><th class="num">Nitrate mg/L</th><th class="num">Arsenic µg/L</th><th class="num">Hardness mg/L</th><th>Potability</th></tr></thead>
            <tbody>${quality.map((q) => `<tr>
              <td>${dateOf(q.sample_date)}</td>
              <td class="num">${q.ph ?? '—'}</td>
              <td class="num">${q.tds_mg_l ?? '—'}</td>
              <td class="num">${q.fluoride_mg_l ?? '—'}</td>
              <td class="num">${q.nitrate_mg_l ?? '—'}</td>
              <td class="num">${q.arsenic_ug_l ?? '—'}</td>
              <td class="num">${q.hardness_mg_l ?? '—'}</td>
              <td><span class="badge ${q.potability === 'potable' ? 'ok' : 'bad'}">${esc(humanize(q.potability))}</span></td>
            </tr>`).join('')}</tbody>
          </table>
        </div>` : ''}
      </section>`

    const dl = body.querySelector('#download-levels')
    if (dl) {
      dl.addEventListener('click', () => {
        if (!levels.length) return
        downloadCsv(`${m.well_id}_levels.csv`, levels.map((l) => ({
          station_id: m.well_id,
          measurement_date: dateOf(l.measurement_date),
          season: l.season,
          depth_to_water_mbgl: l.depth_to_water_mbgl,
          data_quality_flag: l.data_quality_flag,
          measurement_method: l.measurement_method,
        })))
      })
    }

    // Station selection replaces #station-body after the page's initial motion
    // pass; initialize the new dossier panels, counters and chart observers.
    enter(body)
  }

  try {
    const states = await api.states()
    selState.innerHTML = options(states, 'state', 'state')
    const initialState = pending && states.some((s) => s.state === pending.state) ? pending.state : states[0].state
    selState.value = initialState
    await loadDistricts(initialState, pending && pending.district, pending && pending.wellId)
    selState.addEventListener('change', () => loadDistricts(selState.value).catch((e) => { err.innerHTML = errorNote(e.message) }))
    selDistrict.addEventListener('change', () => loadStations(selDistrict.value).catch((e) => { err.innerHTML = errorNote(e.message) }))
    selStation.addEventListener('change', () => loadDetail(selStation.value))
  } catch (e) {
    err.innerHTML = errorNote(e.message)
  }
}
