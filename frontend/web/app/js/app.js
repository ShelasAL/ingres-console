
import { api } from './api.js'
import { getSettings, saveSettings, onSettings, providerLabel } from './store.js'
import { icon, esc, toast } from './ui.js'
import { createPalette } from './palette.js'
import { enter, replayCounts, replayVisuals } from './motion.js?v=20261114-01'
import { getThemePref, getResolvedTheme, setTheme, onTheme } from './theme.js'
import * as Dashboard from './views/dashboard.js?v=20261114-01'
import * as Copilot from './views/copilot.js?v=20261114-01'
import * as MapView from './views/map.js?v=20261114-01'
import * as Stations from './views/stations.js?v=20261114-01'
import * as Explore from './views/explore.js?v=20261114-01'
import * as Performance from './views/performance.js?v=20261114-01'

const GROUPS = [
  {
    label: 'Monitor',
    pages: [
      { key: 'dashboard', label: 'Dashboard', icon: 'grid' },
      { key: 'map', label: 'Station map', icon: 'map' },
    ],
  },
  {
    label: 'Investigate',
    pages: [
      { key: 'copilot', label: 'Copilot', icon: 'chat' },
      { key: 'stations', label: 'Stations', icon: 'pin' },
      { key: 'explore', label: 'Explore', icon: 'table' },
    ],
  },
  {
    label: 'Verify',
    pages: [{ key: 'performance', label: 'Performance', icon: 'bolt' }],
  },
]

const VIEWS = {
  dashboard: Dashboard.mount,
  map: MapView.mount,
  copilot: Copilot.mount,
  stations: Stations.mount,
  explore: Explore.mount,
  performance: Performance.mount,
}

const PAGE_LIST = GROUPS.flatMap((g) => g.pages)
const PAGE_KEYS = PAGE_LIST.map((p) => p.key)
const TITLES = {
  dashboard: 'Dashboard',
  map: 'Station map',
  copilot: 'Groundwater copilot',
  stations: 'Station dossier',
  explore: 'Raw evidence',
  performance: 'Model performance',
}

let current = null
let health = null
let palette = null

/* ── Shell ──────────────────────────────────────────────────── */

function navMarkup() {
  return GROUPS.map((group, i) => `
    <div class="nav-group">
      <div class="nav-label" id="nav-label-${i}">${esc(group.label)}</div>
      ${group.pages.map((p) => `
        <button class="nav-item" data-page="${p.key}" aria-current="false">
          ${icon(p.icon, 17)}<span>${esc(p.label)}</span>
        </button>`).join('')}
    </div>`).join('')
}

function shell() {
  document.getElementById('root').innerHTML = `
    <div class="app">
      <aside class="sidebar" id="sidebar" aria-label="Primary navigation">
        <div class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg class="brand-mark-logo brand-mark-logo--dark" viewBox="0 0 36 36" focusable="false" aria-hidden="true">
              <path class="brand-water" d="M18 5.5c3.8 5 7.3 8.7 7.3 13.1a7.3 7.3 0 1 1-14.6 0C10.7 14.2 14.2 10.5 18 5.5Z"/>
              <path class="brand-strata" d="M8 23.5c2.8-1.8 5.5-1.8 8.2 0s5.4 1.8 8.1 0 5.1-1.8 7.7 0M9.5 28c2.3-1.4 4.7-1.4 7 0s4.7 1.4 7 0 4.4-1.4 6.8 0"/>
            </svg>
            <svg class="brand-mark-logo brand-mark-logo--light" viewBox="0 0 36 36" focusable="false" aria-hidden="true">
              <path class="brand-water" d="M18 5.5c3.8 5 7.3 8.7 7.3 13.1a7.3 7.3 0 1 1-14.6 0C10.7 14.2 14.2 10.5 18 5.5Z"/>
              <path class="brand-strata" d="M8 23.5c2.8-1.8 5.5-1.8 8.2 0s5.4 1.8 8.1 0 5.1-1.8 7.7 0M9.5 28c2.3-1.4 4.7-1.4 7 0s4.7 1.4 7 0 4.4-1.4 6.8 0"/>
            </svg>
          </span>
          <div>
            <div class="brand-name">INGRES</div>
            <div class="brand-sub">Groundwater intelligence</div>
          </div>
          <button class="icon-btn drawer-close" id="drawer-close" aria-label="Close navigation" style="margin-left:auto">${icon('close', 17)}</button>
        </div>
        <nav class="nav">${navMarkup()}</nav>
        <div class="sidebar-foot">
          <div class="status">
            <span class="status-dot" id="status-dot" aria-hidden="true"></span>
            <div>
              <div class="status-title" id="status-title">Connecting…</div>
              <div class="status-sub" id="status-sub">Checking API</div>
            </div>
          </div>
          <button class="btn wide" id="open-settings">${icon('settings', 15)} Model settings</button>
          <div class="sidebar-note">Read-only record · CGWB / NWIC<br>GEC-2015 · BIS 10500:2012</div>
        </div>
      </aside>
      <div class="scrim" id="scrim" aria-hidden="true"></div>

      <main class="main" id="main">
        <header class="topbar">
          <div class="crumbs">
            <button class="icon-btn menu-btn" id="menu-btn" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar">${icon('menu', 17)}</button>
            <span class="root">INGRES</span>
            <span class="sep" aria-hidden="true">/</span>
            <span class="current" id="crumb">Dashboard</span>
          </div>
          <div class="top-actions">
            <button class="search-trigger" id="open-palette" aria-label="Search stations and pages">
              ${icon('search', 15)}<span class="grow">Search stations, pages…</span><kbd>Ctrl K</kbd>
            </button>
          <span class="provider-chip" id="provider-pill">Offline synthesizer</span>
            <button class="icon-btn" id="theme-toggle" aria-label="Switch to light appearance" title="Switch appearance">${icon('sun', 16)}</button>
            <button class="icon-btn" id="top-settings" aria-label="Open model settings">${icon('settings', 16)}</button>
          </div>
        </header>
        <div class="content"><div id="view" class="view" tabindex="-1"></div></div>
      </main>
    </div>

    <dialog class="dialog settings" id="settings-dialog" aria-labelledby="settings-title">
      <form id="settings-form">
        <div class="dialog-head">
          <div>
            <h2 id="settings-title">Model settings</h2>
            <p>The retrieval, coverage and provenance path is identical for every provider. Without a key, the deterministic offline synthesizer answers.</p>
          </div>
          <button type="button" class="icon-btn" id="settings-close" aria-label="Close settings">${icon('close', 16)}</button>
        </div>
        <div class="dialog-body">
          <label class="field">
            <span>Provider</span>
            <select id="s-provider" autofocus>
              <option value="offline">Offline synthesizer — no key</option>
              <option value="openrouter">OpenRouter</option>
              <option value="gemini">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="custom">Custom base URL — local / Ollama</option>
            </select>
          </label>
          <div id="cloud-fields" style="display:none;flex-direction:column;gap:12px">
            <label class="field">
              <span>API key</span>
              <input id="s-key" type="password" autocomplete="off" placeholder="sk-…" />
              <span class="field-hint">Stored in this browser only. Sent with each question, never persisted server-side.</span>
            </label>
            <label class="field">
              <span>Model</span>
              <input id="s-model" type="text" autocomplete="off" placeholder="meta-llama/llama-3.3-70b-instruct" />
            </label>
            <label class="field">
              <span>Base URL <span class="muted" style="text-transform:none;letter-spacing:0">(optional)</span></span>
              <input id="s-url" type="url" autocomplete="off" placeholder="https://openrouter.ai/api/v1" />
            </label>
          </div>
          <div class="dialog-note">${icon('shield', 15)}<span>Keys live in <span class="mono">localStorage</span> on this device. Clear the field and save to remove one.</span></div>
        </div>
        <div class="dialog-foot">
          <button type="button" class="btn ghost" id="settings-cancel">Cancel</button>
          <button type="submit" class="btn primary" id="settings-save">Save settings</button>
        </div>
      </form>
    </dialog>`

  const nav = document.querySelector('#sidebar .nav')
  nav.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-page]')
    if (!btn) return
    closeNav({ restoreFocus: false })
    go(btn.dataset.page)
  })

  document.getElementById('open-settings').addEventListener('click', openSettings)
  document.getElementById('top-settings').addEventListener('click', openSettings)
  document.getElementById('menu-btn').addEventListener('click', openNav)
  document.getElementById('drawer-close').addEventListener('click', () => closeNav())
  document.getElementById('scrim').addEventListener('click', () => closeNav())
  document.getElementById('open-palette').addEventListener('click', () => palette && palette.open())
  document.getElementById('theme-toggle').addEventListener('click', () => {
    const button = document.getElementById('theme-toggle')
    const next = getResolvedTheme() === 'light' ? 'dark' : 'light'
    const change = () => {
      setTheme(next)
      paintThemeButton()
    }
    const view = document.getElementById('view')
    // Counters begin on the click; charts and borders wait for the ripple,
    // then reveal again only when each visual reaches the viewport.
    replayCounts(view, { shineDelayMs: 100 })
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !document.startViewTransition) {
      change()
      replayVisuals(view)
      return
    }
    const rect = button.getBoundingClientRect()
    document.documentElement.style.setProperty('--theme-origin-x', `${rect.left + rect.width / 2}px`)
    document.documentElement.style.setProperty('--theme-origin-y', `${rect.top + rect.height / 2}px`)
    const transition = document.startViewTransition(change)
    transition.finished.then(() => {
      replayVisuals(document.getElementById('view'))
    }).catch(() => {})
  })
  onTheme(paintThemeButton)
  paintThemeButton()
}

function paintThemeButton() {
  const button = document.getElementById('theme-toggle')
  if (!button) return
  const light = getResolvedTheme() === 'light'
  button.innerHTML = icon(light ? 'moon' : 'sun', 16)
  button.setAttribute('aria-label', `Switch to ${light ? 'dark' : 'light'} appearance`)
  button.title = `${light ? 'Dark' : 'Light'} appearance · ${getThemePref() === 'system' ? 'system default' : 'manual'}`
}

/* ── Routing ────────────────────────────────────────────────── */

function pageFromHash() {
  const raw = location.hash.replace(/^#\/?/, '').replace(/\/.*$/, '')
  return PAGE_KEYS.includes(raw) ? raw : 'dashboard'
}

function go(page, opts = {}) {
  if (!PAGE_KEYS.includes(page)) return
  if (page === current && !opts.force) return
  const next = `#/${page}`
  if (location.hash === next) {
    render(page, { focus: true })
  } else {
    location.hash = next
  }
}

function render(page, opts = {}) {
  if (!PAGE_KEYS.includes(page)) page = 'dashboard'
  current = page

  document.querySelectorAll('.nav-item').forEach((b) => {
    const on = b.dataset.page === page
    if (on) b.setAttribute('aria-current', 'page')
    else b.removeAttribute('aria-current')
  })

  const crumb = document.getElementById('crumb')
  if (crumb) crumb.textContent = TITLES[page]
  document.title = page === 'dashboard'
    ? 'INGRES — National Groundwater Intelligence'
    : `${TITLES[page]} · INGRES`

  const old = document.getElementById('view')
  const host = document.createElement('div')
  host.id = 'view'
  host.className = 'view'
  host.tabIndex = -1
  old.replaceWith(host)
  window.scrollTo(0, 0)

  const ctx = { navigate: go }
  try {
    const result = VIEWS[page](host, ctx)
    if (result && typeof result.catch === 'function') {
      result.then(() => enter(host)).catch((err) => {
        host.innerHTML = `<div class="error-note" role="alert">${icon('alert', 15)}<span>${esc(err.message || 'This view failed to load.')}</span></div>`
      })
    } else enter(host)
  } catch (err) {
    host.innerHTML = `<div class="error-note" role="alert">${icon('alert', 15)}<span>${esc(err.message || 'This view failed to load.')}</span></div>`
  }

  if (opts.focus) host.focus({ preventScroll: true })
}

window.addEventListener('hashchange', () => {
  render(pageFromHash(), { focus: true })
})

/* ── Status ─────────────────────────────────────────────────── */

function paintStatus() {
  const live = health && health.status === 'ok'
  const dot = document.getElementById('status-dot')
  if (dot) dot.className = `status-dot ${live ? 'live' : 'down'}`
  const title = document.getElementById('status-title')
  if (title) title.textContent = live ? 'API connected' : 'API offline'
  const sub = document.getElementById('status-sub')
  const label = providerLabel(getSettings())
  if (sub) sub.textContent = live ? label : 'Start the local server'
  const pill = document.getElementById('provider-pill')
  if (pill) {
    pill.textContent = live ? label : 'API offline'
    pill.style.borderColor = live ? '' : 'rgba(240,123,114,.3)'
    pill.style.background = live ? '' : 'rgba(240,123,114,.08)'
    pill.style.color = live ? '' : 'var(--danger)'
  }
}

async function checkHealth() {
  try {
    health = await api.health()
  } catch (e) {
    health = { status: 'offline' }
  }
  paintStatus()
}

/* ── Settings ───────────────────────────────────────────────── */

function openSettings() {
  const dialog = document.getElementById('settings-dialog')
  if (!dialog || dialog.open) return
  const s = getSettings()
  document.getElementById('s-provider').value = s.provider || 'offline'
  document.getElementById('s-key').value = s.apiKey || ''
  document.getElementById('s-model').value = s.model || ''
  document.getElementById('s-url').value = s.baseUrl || ''
  syncProviderFields()
  dialog.showModal()
}

function syncProviderFields() {
  const provider = document.getElementById('s-provider').value
  const fields = document.getElementById('cloud-fields')
  fields.style.display = provider === 'offline' ? 'none' : 'flex'
}

function bindSettings() {
  const dialog = document.getElementById('settings-dialog')
  document.getElementById('s-provider').addEventListener('change', syncProviderFields)
  document.getElementById('settings-close').addEventListener('click', () => dialog.close())
  document.getElementById('settings-cancel').addEventListener('click', () => dialog.close())
  document.getElementById('settings-form').addEventListener('submit', (e) => {
    e.preventDefault()
    const provider = document.getElementById('s-provider').value
    saveSettings({
      provider,
      apiKey: provider === 'offline' ? '' : document.getElementById('s-key').value.trim(),
      model: provider === 'offline' ? '' : document.getElementById('s-model').value.trim(),
      baseUrl: provider === 'offline' ? '' : document.getElementById('s-url').value.trim(),
    })
    dialog.close()
    toast(provider === 'offline' ? 'Offline synthesizer selected' : `${providerLabel(getSettings())} settings saved`)
  })
}

/* ── Mobile drawer ──────────────────────────────────────────── */

let navReturnFocus = null

function focusables(scope) {
  return Array.from(scope.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
    .filter((el) => !el.disabled && el.offsetParent !== null)
}

function openNav() {
  navReturnFocus = document.activeElement
  document.body.classList.add('nav-open')
  document.getElementById('menu-btn').setAttribute('aria-expanded', 'true')
  const close = document.getElementById('drawer-close')
  if (close) close.focus()
}

function closeNav({ restoreFocus = true } = {}) {
  if (!document.body.classList.contains('nav-open')) return
  document.body.classList.remove('nav-open')
  const menu = document.getElementById('menu-btn')
  if (menu) menu.setAttribute('aria-expanded', 'false')
  if (restoreFocus && navReturnFocus && document.contains(navReturnFocus)) navReturnFocus.focus()
  navReturnFocus = null
}

document.addEventListener('keydown', (e) => {
  const drawerOpen = document.body.classList.contains('nav-open')
  if (drawerOpen && e.key === 'Escape') {
    e.preventDefault()
    closeNav()
    return
  }
  if (drawerOpen && e.key === 'Tab') {
    const sidebar = document.getElementById('sidebar')
    const items = focusables(sidebar)
    if (!items.length) return
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    return
  }
  if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    if (palette) palette.open()
  }
})

/* ── Boot ───────────────────────────────────────────────────── */

async function boot() {
  setTheme(getThemePref())
  shell()
  bindSettings()
  palette = createPalette({ pages: PAGE_LIST, navigate: go, openSettings })

  onSettings(paintStatus)
  await checkHealth()

  if (!location.hash || !PAGE_KEYS.includes(pageFromHash())) {
    history.replaceState(null, '', '#/dashboard')
  }
  render(pageFromHash())
}

boot()
