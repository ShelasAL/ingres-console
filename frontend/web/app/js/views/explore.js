
import { api, downloadCsv } from '../api.js'
import { pageHead, spinner, errorNote, emptyState, esc, icon, humanize, fmt } from '../ui.js'

const TABS = [
  ['wells', 'Stations'],
  ['levels', 'Water levels'],
  ['quality', 'Quality samples'],
  ['units', 'GEC units'],
]

const isDate = (key) => /date/i.test(key)
const isYear = (key) => /(^|_)year$/.test(key)

function cell(value, key) {
  if (value === null || value === undefined || value === '') return '<td>—</td>'
  if (isDate(key)) return `<td>${esc(String(value).slice(0, 10))}</td>`
  if (key === 'potability') {
    const tone = value === 'potable' ? 'ok' : 'bad'
    return `<td><span class="badge ${tone}">${esc(humanize(value))}</span></td>`
  }
  if (typeof value === 'number') {
    const text = isYear(key)
      ? String(Math.trunc(value))
      : Number.isInteger(value)
        ? fmt(value)
        : Number(value).toLocaleString('en-IN', { maximumFractionDigits: 3 })
    return `<td class="num">${esc(text)}</td>`
  }
  const cls = /_id$/.test(key) ? ' class="id"' : ''
  return `<td${cls}>${esc(String(value))}</td>`
}

export async function mount(root) {
  let tab = 'wells'
  let state = ''
  let states = []
  let data = null
  let query = ''

  root.innerHTML = `
    ${pageHead({
      eyebrow: 'Verification',
      title: 'Raw evidence',
      lede: 'The four tables that power every answer — stations, water levels, quality samples and GEC-2015 units. Filter, search and export the rows you are shown.',
    })}
    <div id="explore-error"></div>
    <section class="panel explore-toolbar" aria-label="Table controls">
      <div class="seg" id="tabs" role="group" aria-label="Table">
        ${TABS.map(([k, label]) => `<button data-tab="${k}" aria-pressed="${k === tab}">${label}</button>`).join('')}
      </div>
      <div class="explore-tools">
        <label class="search-field">
          <span class="sr-only">Filter rows</span>
          ${icon('search', 14)}
          <input id="row-search" type="search" placeholder="Filter rows…" autocomplete="off" />
        </label>
        <label class="sr-only" for="state-filter">Filter by state</label>
        <select id="state-filter"><option value="">All states</option></select>
        <button class="btn sm" id="download-rows" disabled>${icon('download', 13)} CSV</button>
      </div>
    </section>
    <div id="explore-body">${spinner('Loading rows…')}</div>`

  const tabsEl = root.querySelector('#tabs')
  const stateEl = root.querySelector('#state-filter')
  const searchEl = root.querySelector('#row-search')
  const body = root.querySelector('#explore-body')
  const errEl = root.querySelector('#explore-error')
  const downloadEl = root.querySelector('#download-rows')

  const filteredRows = () => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data.rows
    return data.rows.filter((row) => data.columns.some((c) => String(row[c] ?? '').toLowerCase().includes(q)))
  }

  function renderTable() {
    if (!data) return
    const rows = filteredRows()
    const cols = data.columns
    downloadEl.disabled = !rows.length
    if (!rows.length) {
      body.innerHTML = emptyState(
        query ? 'No rows match this filter' : 'No rows returned',
        query ? `Nothing in ${TABS.find((t) => t[0] === tab)[1].toLowerCase()} matches “${query}”.` : 'Try another table or state.'
      )
      return
    }

    body.innerHTML = `
      <div class="table-meta">
        <span>${fmt(rows.length)} of ${fmt(data.rows.length)} rows</span>
        <span>·</span>
        <span>${cols.length} columns</span>
        <span style="margin-left:auto">Showing at most 200 rows per table and state</span>
      </div>
      <div class="table-wrap tall">
        <table>
          <thead><tr>${cols.map((c) => `<th${typeof data.rows[0][c] === 'number' ? ' class="num"' : ''}>${esc(humanize(c))}</th>`).join('')}</tr></thead>
          <tbody>${rows.map((row) => `<tr>${cols.map((c) => cell(row[c], c)).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>
      <div class="table-note">Each preview is capped server-side; answers and the copilot query the full record.</div>`

    downloadEl.onclick = () => {
      const file = `ingres_${tab}${state ? '_' + state.replace(/\s+/g, '_') : ''}.csv`
      downloadCsv(file, rows)
    }
  }

  async function loadStates() {
    try {
      states = await api.states()
      stateEl.innerHTML = '<option value="">All states</option>' +
        states.map((s) => `<option value="${esc(s.state)}">${esc(s.state)} (${fmt(s.wells)})</option>`).join('')
    } catch (e) {
      errEl.innerHTML = errorNote(e.message)
    }
  }

  async function load() {
    body.innerHTML = spinner('Loading rows…')
    errEl.innerHTML = ''
    try {
      data = await api.explore(tab, state)
      renderTable()
    } catch (e) {
      data = null
      body.innerHTML = ''
      errEl.innerHTML = errorNote(e.message)
    }
  }

  tabsEl.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-tab]')
    if (!btn || btn.dataset.tab === tab) return
    tab = btn.dataset.tab
    query = ''
    searchEl.value = ''
    tabsEl.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.tab === tab)))
    load()
  })

  stateEl.addEventListener('change', () => {
    state = stateEl.value
    load()
  })

  searchEl.addEventListener('input', () => {
    query = searchEl.value
    renderTable()
  })

  await loadStates()
  await load()
}
