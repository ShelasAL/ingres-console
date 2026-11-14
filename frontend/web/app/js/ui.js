// Shared UI primitives: escaping, icons, headings, badges, states, toasts.

export const esc = (v) =>
  String(v === null || v === undefined ? '' : v).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

export const fmt = (n) => Number(n || 0).toLocaleString('en-IN')

export const pct = (n, digits = 1) => `${Number(n || 0).toFixed(digits)}%`

/* A number that counts up when it scrolls into view. The markup already holds
   the exact final value, so no-JS and reduced-motion readers see the truth. */
export function count(value, opts = {}) {
  const n = Number(value || 0)
  const auto = Number.isInteger(n)
    ? 0
    : Math.min(2, (String(n).split('.')[1] || '').replace(/0+$/, '').length || 1)
  const decimals = opts.decimals === undefined ? auto : opts.decimals
  const group = opts.group !== false
  const prefix = opts.prefix || ''
  const suffix = opts.suffix || ''
  const final = prefix + (group
    ? n.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : n.toFixed(decimals)) + suffix
  const cls = opts.className ? ` class="${esc(opts.className)}"` : ''
  return `<span${cls} data-count-to="${n}" data-count-decimals="${decimals}" data-count-group="${group}" data-count-prefix="${esc(prefix)}" data-count-suffix="${esc(suffix)}" aria-label="${esc(final)}">${esc(final)}</span>`
}

export const humanize = (v) => {
  const s = String(v || '').replace(/_/g, ' ')
  // Normalise all-caps enums (STRUCTURED_LEVEL) without disturbing mixed-case names.
  return s && s === s.toUpperCase() ? s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : s
}

export const dateOf = (v) => String(v || '').slice(0, 10)

/* ── Icons ──────────────────────────────────────────────────── */

const ICONS = {
  droplet: '<path d="M12 3s6 6.3 6 10.5A6 6 0 0 1 6 13.5C6 9.3 12 3 12 3Z"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.3"/><rect x="14" y="3" width="7" height="7" rx="1.3"/><rect x="3" y="14" width="7" height="7" rx="1.3"/><rect x="14" y="14" width="7" height="7" rx="1.3"/>',
  map: '<path d="M9 3 3 5v16l6-2 6 2 6-2V3l-6 2-6-2Z"/><path d="M9 3v16M15 5v16"/>',
  chat: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H7l-4 3 1.2-5.1A8.5 8.5 0 1 1 21 11.5Z"/>',
  pin: '<path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11Z"/><circle cx="12" cy="10" r="2.4"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/>',
  settings: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><circle cx="4" cy="12" r="2"/><circle cx="12" cy="10" r="2"/><circle cx="20" cy="14" r="2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  'chevron-right': '<path d="m9 6 6 6-6 6"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'arrow-right': '<path d="M4 12h15M13 6l7 6-7 6"/>',
  download: '<path d="M12 3v11M8 10l4 4 4-4"/><path d="M4 17v3h16v-3"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
  check: '<path d="m4 12.5 5 5L20 6.5"/>',
  alert: '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5M12 17.2v.1"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.1"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.6"/><path d="M20 4v7h-7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  home: '<path d="M4 11 12 4l8 7"/><path d="M6 10v10h12V10"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  shield: '<path d="M12 3 4.5 6v6c0 4.5 3.2 8 7.5 9 4.3-1 7.5-4.5 7.5-9V6L12 3Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
  file: '<path d="M14 3H6v18h12V7l-4-4Z"/><path d="M14 3v4h4"/>',
  play: '<path d="M7 4.5v15l13-7.5-13-7.5Z"/>',
  filter: '<path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z"/>',
  activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z"/>',
}

export function icon(name, size = 18, cls = '') {
  const body = ICONS[name] || ''
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${cls ? ` class="${cls}"` : ''}>${body}</svg>`
}

/* ── Headings ───────────────────────────────────────────────── */

export function pageHead({ eyebrow = '', title, lede = '', meta = [], actions = '' }) {
  const metaHtml = meta.length
    ? `<div class="page-meta">${meta.map((m) => `<span>${m}</span>`).join('')}</div>`
    : ''
  return `<header class="page-head">
    <div>
      ${eyebrow ? `<div class="eyebrow">${esc(eyebrow)}</div>` : ''}
      <h1>${esc(title)}</h1>
      ${lede ? `<p class="lede">${lede}</p>` : ''}
    </div>
    ${actions ? `<div class="page-actions">${actions}</div>` : metaHtml}
  </header>`
}

export function panelHead(title, hint = '', right = '') {
  return `<div class="panel-head">
    <div><h2>${esc(title)}</h2>${hint ? `<p>${hint}</p>` : ''}</div>
    ${right ? `<div class="head-right">${right}</div>` : ''}
  </div>`
}

/* ── Badges ─────────────────────────────────────────────────── */

const STATE = {
  GROUNDED: ['Fully supported', 'ok'],
  PARTIAL: ['Partially supported', 'warn'],
  INFERRED: ['Inferred', 'info'],
  INSUFFICIENT: ['Insufficient data', 'bad'],
  OUT_OF_SCOPE: ['Out of scope', 'neutral'],
  HUMAN_REVIEW: ['Human review', 'warn'],
}
const CONF = { HIGH: 'ok', MEDIUM: 'warn', LOW: 'bad', NONE: 'neutral' }

export function badge(kind, value) {
  if (value === undefined || value === null) return ''
  if (kind === 'state') {
    const s = STATE[value] || [humanize(value), 'neutral']
    return `<span class="badge ${s[1]}">${esc(s[0])}</span>`
  }
  return `<span class="badge ${CONF[value] || 'neutral'}">${esc(value)} confidence</span>`
}

export function chip(text, tone = '') {
  return `<span class="chip ${tone}">${esc(text)}</span>`
}

/* ── States ─────────────────────────────────────────────────── */

export function spinner(label = 'Loading') {
  return `<div class="loading-page"><span class="spinner" aria-hidden="true"></span> ${esc(label)}</div>`
}

export function errorNote(message) {
  return message
    ? `<div class="error-note" role="alert">${icon('alert', 15)}<span>${esc(message)}</span></div>`
    : ''
}

export function emptyState(title, text = '', iconName = 'database') {
  return `<div class="empty">${icon(iconName, 22)}<h3>${esc(title)}</h3>${text ? `<div>${esc(text)}</div>` : ''}</div>`
}

export function skeleton() {
  return `<div aria-hidden="true"><div class="skeleton skel-head"></div><div class="skeleton skel-row"></div><div class="skeleton skel-chart"></div></div>`
}

/* ── Prose ──────────────────────────────────────────────────── */

export function markdownish(text) {
  if (!text) return ''
  return String(text).split(/\r?\n/).map((line) => {
    const t = line.trim()
    if (!t) return '<div class="prose-gap"></div>'
    const bullet = t.startsWith('- ') || t.startsWith('• ')
    const content = bullet ? t.slice(2) : t
    const html = esc(content).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    return bullet
      ? `<div class="prose-bullet"><i></i><div>${html}</div></div>`
      : `<p>${html}</p>`
  }).join('')
}

/* ── Toast ──────────────────────────────────────────────────── */

let toastCount = 0

export function toast(message, tone = 'ok') {
  const region = document.getElementById('toast-region')
  if (!region) return
  while (region.children.length >= 3) region.firstElementChild.remove()
  const el = document.createElement('div')
  el.className = `toast${tone === 'bad' ? ' bad' : ''}`
  el.innerHTML = `${icon(tone === 'bad' ? 'alert' : 'check', 15)}<span>${esc(message)}</span>`
  region.appendChild(el)
  toastCount += 1
  const id = toastCount
  window.setTimeout(() => {
    if (el.dataset.id !== String(id)) return
    el.classList.add('out')
    window.setTimeout(() => el.remove(), 200)
  }, 2800)
}

export async function copyText(value, okMessage = 'Copied to clipboard') {
  try {
    await navigator.clipboard.writeText(String(value || ''))
    toast(okMessage)
  } catch (e) {
    toast('Could not copy in this browser', 'bad')
  }
}
