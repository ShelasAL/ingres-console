// Hand-written SVG charts. No build step, no chart library, no canvas.

import { esc } from './ui.js'

export const SERIES = [
  'var(--series-1)',
  'var(--series-2)',
  'var(--series-3)',
  'var(--series-4)',
  'var(--series-5)',
]

const nf = (n) => Number(n || 0).toLocaleString('en-IN')
let chartSequence = 0

/* Horizontal bars with an optional threshold.
   items: [{ label, value, detail? }] */
export function hBar(items, opts = {}) {
  const glossId = `bar-gloss-${++chartSequence}`
  const unit = opts.unit === undefined ? '%' : opts.unit
  const threshold = opts.threshold === undefined ? null : opts.threshold
  const valueFormat = opts.valueFormat || ((v) => `${v}${unit}`)

  const W = 660
  const rowH = 28
  const padL = 136
  const padR = 58
  const padT = threshold !== null ? 26 : 10
  const padB = 8
  const inner = W - padL - padR
  const H = padT + items.length * rowH + padB
  const max = opts.max || Math.max(threshold || 0, ...items.map((d) => Number(d.value) || 0), 1) * 1.08

  const rows = items.map((d, i) => {
    const y = padT + i * rowH
    const value = Number(d.value) || 0
    const w = Math.max(2, (value / max) * inner)
    const over = threshold !== null && value > threshold
    return `<g style="--i:${i}">
      <text x="${padL - 12}" y="${y + 15}" text-anchor="end" class="c-label">${esc(d.label)}</text>
      <rect x="${padL}" y="${y + 7}" width="${inner}" height="8" rx="3" class="c-track"/>
      <rect x="${padL}" y="${y + 7}" width="${w.toFixed(1)}" height="8" rx="3" class="c-bar${over ? ' over' : ''}" style="--bar-gloss-fill:url(#${glossId});--bar-gloss-fill-light:url(#${glossId}-light)"/>
      <circle class="c-bar-tip${over ? ' over' : ''}" cx="${(padL + w).toFixed(1)}" cy="${y + 11}" r="3.5"/>
      <text x="${padL + inner + 10}" y="${y + 15}" class="c-value">${esc(valueFormat(value))}</text>
    </g>`
  }).join('')

  const thresholdMark = threshold !== null
    ? `<line x1="${padL + (threshold / max) * inner}" x2="${padL + (threshold / max) * inner}" y1="${padT - 4}" y2="${H - 4}" class="c-threshold"/>
       <text x="${padL + (threshold / max) * inner + 6}" y="${padT - 10}" class="c-threshold-label">${threshold}% critical</text>`
    : ''

  const summary = items.map((d) => `${d.label}: ${valueFormat(Number(d.value) || 0)}`).join('; ')
  const gloss = `<defs><linearGradient id="${glossId}" gradientUnits="userSpaceOnUse" x1="-140" y1="0" x2="0" y2="0">
    <stop offset="0" stop-color="#5865f2"/><stop offset=".42" stop-color="#5865f2"/><stop offset=".5" stop-color="#aeb5ff"/><stop offset=".58" stop-color="#5865f2"/><stop offset="1" stop-color="#5865f2"/>
    <animate attributeName="x1" from="-140" to="660" dur="4.8s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1" data-motion-theme="dark"/>
    <animate attributeName="x2" from="0" to="800" dur="4.8s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1" data-motion-theme="dark"/>
  </linearGradient><linearGradient id="${glossId}-light" gradientUnits="userSpaceOnUse" x1="-140" y1="0" x2="0" y2="0">
    <stop offset="0" stop-color="#087f8c"/><stop offset=".42" stop-color="#087f8c"/><stop offset=".5" stop-color="#d5f1e8"/><stop offset=".58" stop-color="#087f8c"/><stop offset="1" stop-color="#087f8c"/>
    <animate attributeName="x1" from="-140" to="660" dur="4.8s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1" data-motion-theme="light"/>
    <animate attributeName="x2" from="0" to="800" dur="4.8s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1" data-motion-theme="light"/>
  </linearGradient></defs>`
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="${esc(opts.label || summary)}">${gloss}${thresholdMark}${rows}</svg>`
}

/* Donut with a legend. items: [{ label, value }] */
export function donut(items, opts = {}) {
  const glossId = `donut-gloss-${++chartSequence}`
  const total = items.reduce((s, d) => s + (Number(d.value) || 0), 0) || 1
  const colors = opts.colors || SERIES
  const r = 74
  const c = 2 * Math.PI * r
  let offset = 0
  const gap = 2.2
  const dominant = items.reduce((best, d, i, list) => Number(d.value) > Number(list[best]?.value || -Infinity) ? i : best, 0)
  const segs = items.map((d, i) => {
    const value = Number(d.value) || 0
    const dash = Math.max(0, (value / total) * c - gap)
    const attrs = `style="--i:${i};--dash:${dash.toFixed(2)};--circumference:${c.toFixed(2)};--offset:${(-offset).toFixed(2)}" cx="100" cy="100" r="${r}" fill="none" stroke-width="20" stroke-dasharray="${dash.toFixed(2)} ${(c - dash).toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}" transform="rotate(-90 100 100)"`
    const shineSeg = i === dominant
      ? `<circle class="c-donut-shine" ${attrs} stroke="url(#${glossId})" aria-hidden="true"/>`
      : ''
    const seg = `<circle class="c-donut-seg" ${attrs} stroke="${colors[i % colors.length]}"><title>${esc(d.label)}: ${nf(value)}</title></circle>${shineSeg}`
    offset += (value / total) * c
    return seg
  }).join('')

  const legend = items.map((d, i) => {
    const share = Math.round(((Number(d.value) || 0) / total) * 100)
    return `<div class="legend-row">
      <span class="legend-swatch" style="background:${colors[i % colors.length]}"></span>
      <span class="legend-label">${esc(d.label)}</span>
      <span class="legend-value">${nf(d.value)} <span class="muted" style="font-weight:400">· ${share}%</span></span>
    </div>`
  }).join('')

  const shine = `<defs><linearGradient id="${glossId}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="200" y2="200">
    <stop offset="0%" stop-color="#fff" stop-opacity="0"/><stop offset="46%" stop-color="#fff" stop-opacity="0"/><stop offset="50%" stop-color="#fff" stop-opacity=".88"/><stop offset="54%" stop-color="#fff" stop-opacity="0"/><stop offset="100%" stop-color="#fff" stop-opacity="0"/>
    <animateTransform attributeName="gradientTransform" type="rotate" from="0 100 100" to="360 100 100" dur="5.4s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1"/>
  </linearGradient><linearGradient id="${glossId}-total" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="120" y2="0">
    <stop offset="0" stop-color="var(--ink)"/><stop offset=".42" stop-color="var(--ink)"/><stop offset=".5" stop-color="#fff8e8"/><stop offset=".58" stop-color="var(--ink)"/><stop offset="1" stop-color="var(--ink)"/>
    <animate attributeName="x1" from="30" to="140" dur="5.5s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1"/><animate attributeName="x2" from="110" to="220" dur="5.5s" repeatCount="indefinite" begin="indefinite" data-motion-animate="1"/>
  </linearGradient></defs>`
  return `<div class="donut-wrap">
    <svg viewBox="0 0 200 200" class="donut" role="img" aria-label="${esc(opts.label || 'Distribution')}: ${esc(items.map((d) => `${d.label} ${nf(d.value)}`).join(', '))}">
      ${shine}<circle class="c-donut-track" cx="100" cy="100" r="${r}" fill="none" stroke-width="20"/>
      ${segs}
      <text x="100" y="97" text-anchor="middle" class="donut-total" style="--donut-metal-fill:url(#${glossId}-total)" data-count-to="${total}" data-count-decimals="0" data-count-group="true" data-count-prefix="" data-count-suffix="" aria-label="${nf(total)}">${nf(total)}</text>
      <text x="100" y="115" text-anchor="middle" class="donut-cap">${esc(opts.label || 'total')}</text>
    </svg>
    <div class="legend">${legend}</div>
  </div>`
}

/* Depth-to-water hydrograph. points: [{ x, y }] */
export function line(points, opts = {}) {
  const height = opts.height || 250
  const width = 760
  const pad = { l: 46, r: 16, t: 16, b: 36 }
  const innerW = width - pad.l - pad.r
  const innerH = height - pad.t - pad.b
  if (!points || !points.length) return '<div class="chart-empty">No readings for this station.</div>'

  const ys = points.map((p) => Number(p.y))
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const span = maxY - minY || 1
  const xFor = (i) => pad.l + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  // Depth increases downward: larger mbgl sits lower on the chart.
  const yFor = (v) => pad.t + ((v - minY) / span) * innerH

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)} ${yFor(Number(p.y)).toFixed(1)}`).join(' ')
  const baseY = (pad.t + innerH).toFixed(1)
  const area = `${path} L${xFor(points.length - 1).toFixed(1)} ${baseY} L${xFor(0).toFixed(1)} ${baseY} Z`
  const grid = Array.from({ length: 4 }).map((_, i) => {
    const v = minY + (span * i) / 3
    const y = yFor(v)
    return `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" class="c-grid"/>
      <text x="${pad.l - 9}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="c-axis">${v.toFixed(1)}</text>`
  }).join('')

  const dotR = points.length > 40 ? 1.7 : 2.6
  const dots = points.map((p, i) => {
    const last = i === points.length - 1
    return `<circle cx="${xFor(i).toFixed(1)}" cy="${yFor(Number(p.y)).toFixed(1)}" r="${last ? 3.6 : dotR}" class="${last ? 'c-dot-last' : 'c-dot'}"><title>${esc(String(p.x).slice(0, 10))} · ${Number(p.y).toFixed(2)} mbgl</title></circle>`
  }).join('')

  const idxs = Array.from(new Set([0, Math.floor(points.length / 3), Math.floor((2 * points.length) / 3), points.length - 1]))
  const labels = idxs.filter((idx) => points[idx]).map((idx) => {
    const x = xFor(idx)
    const anchor = idx === 0 ? 'start' : idx === points.length - 1 ? 'end' : 'middle'
    return `<text x="${x.toFixed(1)}" y="${height - 12}" text-anchor="${anchor}" class="c-axis">${esc(String(points[idx].x).slice(0, 10))}</text>`
  }).join('')

  const last = points[points.length - 1]
  return `<svg viewBox="0 0 ${width} ${height}" class="chart" role="img" aria-label="${esc(opts.label || `Depth to water over ${points.length} readings, latest ${Number(last.y).toFixed(2)} metres below ground`)}">
    ${grid}
    <path d="${area}" class="c-area"/>
    <path d="${path}" pathLength="1" class="c-line"/>
    <g class="c-dots">${dots}</g>${labels}
    <text x="12" y="${pad.t + innerH / 2}" transform="rotate(-90 12 ${pad.t + innerH / 2})" text-anchor="middle" class="c-y-title">${esc(opts.yLabel || 'depth to water · mbgl')}</text>
  </svg>`
}

/* Compact labelled bars for categories. items: [{ label, value, tone? }] */
export function miniBars(items, opts = {}) {
  const max = Math.max(...items.map((d) => Number(d.value) || 0), 1)
  return `<div class="mini-bars">${items.map((d, i) => {
    const w = Math.max(3, Math.round(((Number(d.value) || 0) / max) * 100))
    const tone = d.tone ? ` ${d.tone}` : ''
    return `<div class="mini-row" style="--i:${i}">
      <span class="mini-label">${esc(d.label)}</span>
      <span class="mini-track"><span class="mini-fill${tone}" style="--target-width:${w}%"></span></span>
      <span class="mini-value">${nf(d.value)}</span>
    </div>`
  }).join('')}</div>`
}
