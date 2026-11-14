
// Command palette (Ctrl/Cmd K). Instant open — keyboard surfaces should not animate.

import { api } from './api.js'
import { setPendingStation } from './store.js'
import { icon, esc, humanize } from './ui.js'

export function createPalette({ pages, navigate, openSettings }) {
  const root = document.getElementById('dialog-root')
  root.innerHTML = `
    <dialog class="dialog palette" id="palette-dialog" aria-label="Command palette">
      <div class="palette-search">
        ${icon('search', 17)}
        <input id="palette-input" type="text" role="combobox" aria-expanded="true"
               aria-controls="palette-list" aria-autocomplete="list"
               placeholder="Search stations, pages or actions…" autocomplete="off" spellcheck="false" />
        <kbd>esc</kbd>
      </div>
      <div class="palette-list" id="palette-list" role="listbox" aria-label="Results"></div>
      <div class="palette-foot">
        <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
        <span><kbd>↵</kbd> open</span>
        <span class="grow"></span>
        <span id="palette-count"></span>
      </div>
    </dialog>`

  const dialog = document.getElementById('palette-dialog')
  const input = document.getElementById('palette-input')
  const list = document.getElementById('palette-list')
  const count = document.getElementById('palette-count')

  let items = []
  let active = 0
  let stations = null
  let loadingStations = false
  let loadError = false

  function baseItems() {
    return [
      ...pages.map((p) => ({
        id: `page-${p.key}`,
        group: 'Navigate',
        title: p.label,
        sub: `Page · ${p.key}`,
        icon: p.icon,
        run: () => navigate(p.key),
      })),
      {
        id: 'action-settings',
        group: 'Actions',
        title: 'Model settings',
        sub: 'Provider, API key, model',
        icon: 'settings',
        run: () => openSettings(),
      },
      {
        id: 'action-reload',
        group: 'Actions',
        title: 'Reload the record',
        sub: 'Re-fetch the current view',
        icon: 'refresh',
        run: () => window.location.reload(),
      },
    ]
  }

  function filteredBase(q) {
    if (!q) return baseItems()
    return baseItems().filter((it) =>
      it.title.toLowerCase().includes(q) || it.sub.toLowerCase().includes(q))
  }

  function stationItems(q) {
    if (!stations || !q) return []
    const scored = []
    for (const row of stations) {
      const id = String(row.well_id || '').toLowerCase()
      const district = String(row.district || '').toLowerCase()
      const state = String(row.state || '').toLowerCase()
      let score = -1
      if (id.startsWith(q)) score = 0
      else if (id.includes(q)) score = 1
      else if (district.startsWith(q)) score = 2
      else if (district.includes(q)) score = 3
      else if (state.includes(q)) score = 4
      if (score >= 0) scored.push({ row, score })
      if (scored.length > 900) break
    }
    scored.sort((a, b) => a.score - b.score || String(a.row.well_id).localeCompare(String(b.row.well_id)))
    return scored.slice(0, 12).map(({ row }) => ({
      id: `station-${row.well_id}`,
      group: 'Stations',
      title: row.well_id,
      sub: [row.district, row.state].filter(Boolean).join(' · '),
      meta: row.potability ? humanize(row.potability) : 'no sample',
      icon: 'pin',
      run: () => {
        setPendingStation({ state: row.state, district: row.district, wellId: row.well_id })
        navigate('stations', { force: true })
      },
    }))
  }

  function render() {
    const q = input.value.trim().toLowerCase()
    const base = filteredBase(q)
    const stationList = stationItems(q)
    items = [...base, ...stationList]
    if (active >= items.length) active = Math.max(0, items.length - 1)

    let html = ''
    let lastGroup = null
    items.forEach((it, i) => {
      if (it.group !== lastGroup) {
        html += `<div class="palette-group">${esc(it.group)}</div>`
        lastGroup = it.group
      }
      html += `<div class="palette-item" role="option" id="palette-opt-${i}" data-index="${i}" aria-selected="${i === active}" tabindex="-1">
        ${icon(it.icon || 'arrow-right', 16)}
        <span class="p-main">
          <span class="p-title">${esc(it.title)}</span>
          ${it.sub ? `<span class="p-sub">${esc(it.sub)}</span>` : ''}
        </span>
        ${it.meta ? `<span class="p-meta">${esc(it.meta)}</span>` : ''}
      </div>`
    })

    if (!items.length) {
      html = `<div class="palette-empty">${q
        ? `No match for “${esc(input.value.trim())}”`
        : 'Type a station ID, district, state or page.'}</div>`
    } else if (q && !stationList.length && !stations && loadingStations) {
      html += `<div class="palette-group">Stations</div><div class="palette-empty">Loading the station index…</div>`
    } else if (q && !stationList.length && loadError) {
      html += `<div class="palette-group">Stations</div><div class="palette-empty">Station index unavailable.</div>`
    }

    list.innerHTML = html
    input.setAttribute('aria-activedescendant', items.length ? `palette-opt-${active}` : '')

    const activeEl = document.getElementById(`palette-opt-${active}`)
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' })

    if (stations) {
      count.textContent = q
        ? `${stationList.length} of ${stations.length.toLocaleString('en-IN')} stations`
        : `${stations.length.toLocaleString('en-IN')} stations indexed`
    } else if (loadingStations) {
      count.textContent = 'Loading stations…'
    } else if (loadError) {
      count.textContent = 'Pages only'
    } else {
      count.textContent = 'Type to search the station index'
    }
  }

  function move(delta) {
    if (!items.length) return
    active = (active + delta + items.length) % items.length
    render()
  }

  function run(index) {
    const it = items[index]
    if (!it) return
    dialog.close()
    window.setTimeout(() => it.run(), 0)
  }

  async function ensureStations() {
    if (stations || loadingStations) return
    loadingStations = true
    render()
    try {
      stations = await api.mapStations('')
      loadError = false
    } catch (e) {
      stations = null
      loadError = true
    } finally {
      loadingStations = false
      if (dialog.open) render()
    }
  }

  input.addEventListener('input', () => {
    active = 0
    render()
  })

  // A native modal dialog reports clicks on its backdrop as clicks on the
  // dialog itself; clicks inside the search/list bubble from child elements.
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close()
  })

  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
    else if (e.key === 'Enter') { e.preventDefault(); run(active) }
    else if (e.key === 'Escape') { e.preventDefault(); dialog.close() }
  })

  list.addEventListener('mousedown', (e) => {
    // Keep focus in the input; selection is handled on click.
    if (e.target.closest('.palette-item')) e.preventDefault()
  })
  list.addEventListener('click', (e) => {
    const item = e.target.closest('.palette-item')
    if (item) run(Number(item.dataset.index))
  })

  dialog.addEventListener('close', () => {
    input.value = ''
    items = []
    active = 0
    list.innerHTML = ''
  })

  return {
    open() {
      if (dialog.open) { input.focus(); return }
      input.value = ''
      active = 0
      loadError = false
      render()
      dialog.showModal()
      input.focus()
      ensureStations()
    },
  }
}
