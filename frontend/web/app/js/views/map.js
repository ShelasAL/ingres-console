
import { api } from '../api.js'
import { setPendingStation } from '../store.js'
import { pageHead, spinner, errorNote, esc, icon, humanize, fmt } from '../ui.js'

const W = 900
const H = 620
const PAD = 30
const POT_COLORS = {
  potable: '#45d193',
  non_potable: '#f07b72',
  marginal: '#e5b455',
  unknown: '#55646d',
}

const potColor = (r) => POT_COLORS[r.potability] || POT_COLORS.unknown
const potLabel = (r) => (r.potability ? humanize(r.potability) : 'no sample')
const potRank = (r) => (r.potability === 'non_potable' ? 3 : r.potability === 'marginal' ? 2 : r.potability === 'potable' ? 1 : 0)
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

let geoCache = null

async function loadGeo() {
  if (!geoCache) {
    const res = await fetch('/data/india_states.geojson')
    if (!res.ok) throw new Error(`Boundary file failed to load (${res.status})`)
    geoCache = await res.json()
  }
  return geoCache
}

function ringsOf(geometry) {
  if (!geometry) return []
  if (geometry.type === 'Polygon') return [geometry.coordinates]
  if (geometry.type === 'MultiPolygon') return geometry.coordinates
  return []
}

function buildLayout(geo) {
  let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90
  geo.features.forEach((f) => {
    ringsOf(f.geometry).forEach((poly) => poly.forEach((ring) => ring.forEach(([lon, lat]) => {
      if (lon < minLon) minLon = lon
      if (lon > maxLon) maxLon = lon
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    })))
  })
  const k = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180)
  const spanX = (maxLon - minLon) * k
  const spanY = maxLat - minLat
  const scale = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY)
  const offX = (W - spanX * scale) / 2
  const offY = (H - spanY * scale) / 2
  const project = (lon, lat) => ({
    x: offX + (lon - minLon) * k * scale,
    y: H - offY - (lat - minLat) * scale,
  })

  const states = geo.features.map((f) => {
    let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9
    const paths = []
    ringsOf(f.geometry).forEach((poly) => poly.forEach((ring) => {
      const d = ring.map(([lon, lat], i) => {
        const p = project(lon, lat)
        x1 = Math.min(x1, p.x); y1 = Math.min(y1, p.y)
        x2 = Math.max(x2, p.x); y2 = Math.max(y2, p.y)
        return (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ' ' + p.y.toFixed(1)
      }).join(' ') + ' Z'
      paths.push(d)
    }))
    return { name: f.properties.name, paths, bbox: [x1, y1, x2, y2] }
  })
  return { project, states }
}

function fitBox(bbox, pad = 30) {
  const [x1, y1, x2, y2] = bbox
  const bw = Math.max(x2 - x1, 10)
  const bh = Math.max(y2 - y1, 10)
  const scale = Math.min((W - 2 * pad) / bw, (H - 2 * pad) / bh)
  const w = W / scale
  const h = H / scale
  return { x: (x1 + x2) / 2 - w / 2, y: (y1 + y2) / 2 - h / 2, w, h }
}

export async function mount(root, ctx) {
  let state = ''
  let rows = []
  let states = []
  let selected = null
  let detail = null
  let layout = null
  let vb = { x: 0, y: 0, w: W, h: H }
  let dragged = false
  let tweenFrame = null
  let baseDotRadius = 1.25
  let dotScale = 1
  const coarse = window.matchMedia('(pointer: coarse)').matches
  const mapHint = coarse
    ? 'Pinch to zoom · drag to pan · tap a station'
    : 'Scroll to zoom · drag to pan · click a station'

  root.innerHTML = `
    ${pageHead({
      eyebrow: 'Spatial record',
      title: 'Station map',
      lede: 'Every geolocated monitoring station, coloured by the potability of its latest laboratory sample. Choose a state to zoom, then select a station to inspect it.',
    })}
    <div id="map-error"></div>
    <div class="map-layout">
      <section class="panel map-card" aria-label="India station map">
        <div class="map-toolbar">
          <div class="map-title"><strong id="map-count">Loading…</strong></div>
          <label class="sr-only" for="map-state">Filter by state</label>
          <select id="map-state"><option value="">All states</option></select>
        </div>
        <div class="map-frame">
          <div id="map-holder">${spinner('Loading boundaries and stations…')}</div>
          <div class="map-controls">
            <button class="map-btn" id="zoom-in" aria-label="Zoom in">${icon('plus', 15)}</button>
            <button class="map-btn" id="zoom-out" aria-label="Zoom out">${icon('minus', 15)}</button>
            <button class="map-btn" id="zoom-reset" aria-label="Reset view">${icon('home', 15)}</button>
          </div>
        </div>
        <div class="map-legend">
          <span><i style="background:${POT_COLORS.potable}"></i>Potable</span>
          <span><i style="background:${POT_COLORS.non_potable}"></i>Non-potable</span>
          <span><i style="background:${POT_COLORS.marginal}"></i>Marginal</span>
          <span><i style="background:${POT_COLORS.unknown}"></i>No sample</span>
          <span class="legend-note">White ring = suspect or estimated level reading</span>
        </div>
        <div class="map-caption">
          <span>${mapHint}</span>
          <span id="map-scope"></span>
        </div>
      </section>

      <aside class="panel inspector" id="map-panel" aria-live="polite">
        <div class="inspector-empty">${icon('pin', 24)}<div>Select a station on the map<br>to see its profile.</div></div>
      </aside>
    </div>`

  const holder = root.querySelector('#map-holder')
  const panel = root.querySelector('#map-panel')
  const countEl = root.querySelector('#map-count')
  const stateSel = root.querySelector('#map-state')
  const err = root.querySelector('#map-error')
  const scopeEl = root.querySelector('#map-scope')

  function applyView() {
    const svg = holder.querySelector('svg')
    if (svg) svg.setAttribute('viewBox', `${vb.x.toFixed(1)} ${vb.y.toFixed(1)} ${vb.w.toFixed(1)} ${vb.h.toFixed(1)}`)
  }

  function syncDotScale(force = false) {
    const zoom = W / vb.w
    // Counter-scale the markers so the map can reveal detail without turning
    // dense station regions into solid blobs. Mutate only after meaningful
    // zoom steps, never on every animation frame.
    const nextScale = Math.max(0.22, Math.pow(zoom, -1.12))
    if (!force && Math.abs(nextScale - dotScale) < 0.07) return
    dotScale = nextScale
    holder.querySelectorAll('.station-dot').forEach((dot) => {
      const selectedDot = dot.getAttribute('data-id') === selected
      dot.setAttribute('r', ((selectedDot ? 4.2 : baseDotRadius) * dotScale).toFixed(2))
    })
  }

  function cancelTween() {
    if (tweenFrame) cancelAnimationFrame(tweenFrame)
    tweenFrame = null
  }

  function tweenTo(target, duration = 320) {
    cancelTween()
    if (reducedMotion()) { vb = { ...target }; applyView(); return }
    const from = { ...vb }
    const t0 = performance.now()
    const step = (now) => {
      const t = Math.min(1, (now - t0) / duration)
      const e = 1 - Math.pow(1 - t, 3)
      vb = {
        x: from.x + (target.x - from.x) * e,
        y: from.y + (target.y - from.y) * e,
        w: from.w + (target.w - from.w) * e,
        h: from.h + (target.h - from.h) * e,
      }
      applyView()
       if (t < 1) tweenFrame = requestAnimationFrame(step)
       else { tweenFrame = null; syncDotScale() }
    }
    tweenFrame = requestAnimationFrame(step)
  }

  function paintStates() {
    const active = state || null
    holder.querySelectorAll('.state-shape').forEach((p) => {
      const isActive = active && p.getAttribute('data-name') === active
      p.classList.toggle('active', !!isActive)
      p.classList.toggle('dim', !!active && !isActive)
    })
  }

  function renderMap() {
    if (!layout) return
    baseDotRadius = rows.length > 1200 ? 1.25 : rows.length > 400 ? 1.6 : 2.2
    const ordered = rows.slice().sort((a, b) => potRank(a) - potRank(b))
    const statePaths = layout.states.map((st) =>
      `<path class="state-shape" data-name="${esc(st.name)}" d="${st.paths.join(' ')}"><title>${esc(st.name)}</title></path>`).join('')
    const dots = ordered.map((r) => {
      const p = layout.project(Number(r.longitude), Number(r.latitude))
      const flagged = r.data_quality_flag && r.data_quality_flag !== 'good'
      const radius = (selected === r.well_id ? 4.2 : baseDotRadius) * dotScale
      return `<circle class="station-dot ${selected === r.well_id ? 'selected' : ''}" data-id="${esc(r.well_id)}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${radius.toFixed(2)}" fill="${potColor(r)}" ${flagged ? 'stroke="#e7eef1" stroke-width="0.6"' : ''}><title>${esc(r.well_id)} · ${esc(r.district || '')} · ${potLabel(r)}${flagged ? ' · level ' + r.data_quality_flag : ''} · ${esc(humanize(r.well_type))}</title></circle>`
    }).join('')

    holder.innerHTML = `
      <svg class="map-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="India state boundaries with ${fmt(rows.length)} groundwater monitoring stations">
        <defs>
          <pattern id="map-grid" width="22" height="22" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r=".6" class="map-grid-dot"/>
          </pattern>
        </defs>
        <rect x="0" y="0" width="${W}" height="${H}" fill="#070b0e"/>
        <rect x="0" y="0" width="${W}" height="${H}" fill="url(#map-grid)"/>
        <g class="states">${statePaths}</g>
        <g class="dots">${dots}</g>
      </svg>`
    applyView()
    syncDotScale(true)
    paintStates()
    countEl.textContent = `${fmt(rows.length)} stations${state ? ' · ' + state : ' · all states'}`
    scopeEl.textContent = state ? `${state} · zoomed` : 'India · full extent'
    bindMapEvents()
  }

  function renderPanel() {
    if (!selected) {
      panel.innerHTML = `<div class="inspector-empty">${icon('pin', 24)}<div>Select a station on the map<br>to see its profile.</div></div>`
      return
    }
    if (!detail) {
      panel.innerHTML = spinner('Loading station…')
      return
    }
    const m = detail.meta
    const levels = detail.levels || []
    const quality = detail.quality || []
    const latest = levels.length ? levels[levels.length - 1] : null
    const good = levels.filter((l) => l.data_quality_flag === 'good').length
    const health = levels.length ? Math.round((good / levels.length) * 1000) / 10 : 0
    const q = quality[0]
    const potTone = q ? (q.potability === 'potable' ? 'ok' : 'bad') : 'neutral'

    panel.innerHTML = `
      <div class="inspector-head">
        <div>
          <div class="inspector-kicker">Station</div>
          <h2>${esc(m.well_id)}</h2>
        </div>
        ${q ? `<span class="badge ${potTone}">${esc(humanize(q.potability))}</span>` : '<span class="badge neutral">No sample</span>'}
      </div>
      <div class="inspector-sub">${esc(m.district)}, ${esc(m.state)}</div>

      <div class="health-line">
        <span>Telemetry</span>
        <span class="health-track"><span class="health-fill" style="width:${health}%;background:${health > 80 ? 'var(--success)' : health > 50 ? 'var(--warning)' : 'var(--danger)'}"></span></span>
        <span class="tnum">${health}%</span>
      </div>

      <div class="kv"><span>Aquifer</span><strong>${esc(humanize(m.aquifer_type) || '—')}</strong></div>
      <div class="kv"><span>Well type</span><strong>${esc(humanize(m.well_type) || '—')}</strong></div>
      <div class="kv"><span>Borehole depth</span><strong>${m.depth_mbgl === null ? '—' : m.depth_mbgl + ' mbgl'}</strong></div>
      <div class="kv"><span>Installed</span><strong>${m.installation_year || '—'}</strong></div>
      <div class="kv"><span>Coordinates</span><strong>${Number(m.latitude).toFixed(3)}, ${Number(m.longitude).toFixed(3)}</strong></div>
      <div class="kv"><span>Readings</span><strong>${levels.length} · ${health}% good</strong></div>
      <div class="kv"><span>Latest depth</span><strong>${latest ? latest.depth_to_water_mbgl + ' mbgl' : '—'}</strong></div>
      <div class="kv"><span>Latest sample</span><strong>${latest ? String(latest.measurement_date).slice(0, 10) : '—'}</strong></div>
      <div class="kv"><span>Level flag</span><strong>${latest ? esc(humanize(latest.data_quality_flag)) : '—'}</strong></div>

      <button class="btn primary wide" id="open-dossier" style="margin-top:16px">Open full dossier</button>
      <div class="table-note" style="text-align:center">Adds the hydrograph, BIS quality cards and raw telemetry.</div>`

    panel.querySelector('#open-dossier').addEventListener('click', () => {
      setPendingStation({ state: m.state, district: m.district, wellId: m.well_id })
      ctx.navigate('stations', { force: true })
    })
  }

  function zoomAt(cx, cy, factor) {
    cancelTween()
    const nextW = Math.min(W, Math.max(70, vb.w * factor))
    const nextH = nextW * (H / W)
    vb = {
      x: cx - (cx - vb.x) * (nextW / vb.w),
      y: cy - (cy - vb.y) * (nextH / vb.h),
      w: nextW,
      h: nextH,
    }
    applyView()
    syncDotScale()
  }

  function bindMapEvents() {
    const svg = holder.querySelector('svg')
    if (!svg) return
    svg.addEventListener('wheel', (e) => {
      e.preventDefault()
      cancelTween()
      const rect = svg.getBoundingClientRect()
      const cx = vb.x + ((e.clientX - rect.left) / rect.width) * vb.w
      const cy = vb.y + ((e.clientY - rect.top) / rect.height) * vb.h
      zoomAt(cx, cy, e.deltaY < 0 ? 0.82 : 1.22)
    }, { passive: false })

    let start = null
    let downDot = null
    svg.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return
      cancelTween()
      downDot = e.target.closest('[data-id]') ? e.target.closest('[data-id]').getAttribute('data-id') : null
      start = { x: e.clientX, y: e.clientY, vb: { ...vb } }
      dragged = false
      svg.setPointerCapture(e.pointerId)
      svg.classList.add('grabbing')
    })
    svg.addEventListener('pointermove', (e) => {
      if (!start) return
      const rect = svg.getBoundingClientRect()
      const dx = e.clientX - start.x
      const dy = e.clientY - start.y
      if (Math.abs(dx) + Math.abs(dy) > 4) dragged = true
      if (!dragged) return
      vb.x = start.vb.x - (dx / rect.width) * vb.w
      vb.y = start.vb.y - (dy / rect.height) * vb.h
      applyView()
    })
    const end = async () => {
      if (start && !dragged && downDot) {
        const id = downDot
        selected = id
        detail = null
        paintSelection()
        renderPanel()
        try {
          detail = await api.station(id)
          renderPanel()
        } catch (exc) {
          panel.innerHTML = errorNote(exc.message)
        }
      }
      start = null
      downDot = null
      svg.classList.remove('grabbing')
    }
    svg.addEventListener('pointerup', end)
    svg.addEventListener('pointercancel', () => { start = null; downDot = null; svg.classList.remove('grabbing') })
    svg.addEventListener('dblclick', () => { resetView() })
  }

  function paintSelection() {
    holder.querySelectorAll('.station-dot').forEach((c) => {
      const on = c.getAttribute('data-id') === selected
      c.classList.toggle('selected', on)
      c.setAttribute('r', ((on ? 4.2 : baseDotRadius) * dotScale).toFixed(2))
    })
  }

  function resetView(smooth = true) {
    const target = state
      ? (() => {
          const st = layout.states.find((s) => s.name === state)
          return st ? fitBox(st.bbox) : { x: 0, y: 0, w: W, h: H }
        })()
      : { x: 0, y: 0, w: W, h: H }
    if (smooth) tweenTo(target)
    else { cancelTween(); vb = { ...target }; applyView() }
  }

  root.querySelector('#zoom-in').addEventListener('click', () => tweenTo({
    x: vb.x + vb.w * 0.1, y: vb.y + vb.h * 0.1, w: vb.w * 0.8, h: vb.h * 0.8,
  }, 220))
  root.querySelector('#zoom-out').addEventListener('click', () => {
    const nw = Math.min(W, vb.w * 1.25)
    const nh = nw * (H / W)
    tweenTo({ x: vb.x + vb.w / 2 - nw / 2, y: vb.y + vb.h / 2 - nh / 2, w: nw, h: nh }, 220)
  })
  root.querySelector('#zoom-reset').addEventListener('click', () => resetView())

  stateSel.addEventListener('change', () => {
    state = stateSel.value
    selected = null
    detail = null
    renderPanel()
    load().then(() => { resetView(); paintStates() })
  })

  async function load() {
    holder.innerHTML = spinner('Loading stations…')
    err.innerHTML = ''
    try {
      rows = await api.mapStations(state)
      renderMap()
    } catch (exc) {
      holder.innerHTML = ''
      err.innerHTML = errorNote(exc.message)
    }
  }

  try {
    const geo = await loadGeo()
    layout = buildLayout(geo)
    states = await api.states()
    stateSel.innerHTML = '<option value="">All states</option>' +
      states.map((s) => `<option value="${esc(s.state)}">${esc(s.state)} (${fmt(s.wells)})</option>`).join('')
    await load()
  } catch (exc) {
    err.innerHTML = errorNote(exc.message)
  }
}
