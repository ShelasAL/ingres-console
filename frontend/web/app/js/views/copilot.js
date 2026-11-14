
import { api, downloadCsv } from '../api.js'
import { getSettings } from '../store.js'
import { pageHead, badge, chip, markdownish, esc, errorNote, icon, copyText, humanize, fmt } from '../ui.js'
import { line, hBar } from '../charts.js?v=20261114-01'
import { enter } from '../motion.js?v=20261114-01'

const SUGGESTIONS = [
  'What is the fluoride level in Nalgonda wells?',
  'Which districts in Rajasthan are over-exploited?',
  'What is the water level trend in Jaipur from 2015 to 2023?',
  'Is Surat groundwater potable?',
]

let messages = [{ kind: 'intro' }]
let busy = false
let seq = 0
let requestController = null

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

function chartFor(result) {
  const chart = result.chart
  if (!chart || !chart.x || !chart.x.length) return ''
  const inner = chart.type === 'line'
    ? line(chart.x.map((x, i) => ({ x, y: chart.y[i] })), { height: 230, label: chart.title })
    : hBar(
        chart.x.slice(0, 10).map((x, i) => ({ label: String(x).slice(0, 10), value: chart.y[i] })),
        { unit: '', max: Math.max(...chart.y) * 1.12, label: chart.title }
      )
  return `<div class="answer-chart">
    <div class="table-meta">${esc(chart.title || 'Retrieved values')}</div>
    ${inner}
  </div>`
}

function evidenceTable(ev) {
  const keys = Array.from(new Set(ev.flatMap((r) => Object.keys(r)))).slice(0, 8)
  return `<div class="table-wrap medium" style="margin-top:12px">
    <table>
      <thead><tr>${keys.map((k) => `<th>${esc(humanize(k))}</th>`).join('')}</tr></thead>
      <tbody>${ev.slice(0, 12).map((row) => `<tr>${keys.map((k) => `<td>${row[k] === null || row[k] === undefined ? '—' : esc(String(row[k]))}</td>`).join('')}</tr>`).join('')}</tbody>
    </table>
  </div>`
}

function answer(result) {
  const ev = result.evidence || []
  const coverageTone = result.coverage.status === 'FULL' ? 'ok' : result.coverage.status === 'INSUFFICIENT' ? 'bad' : 'warn'

  return `
    <div class="answer" data-result="${result.id}">
      <div class="answer-head">
        ${badge('state', result.state)}
        ${badge('confidence', result.confidence)}
        ${chip(humanize(result.intent), '')}
        ${chip(`coverage ${result.coverage.status.toLowerCase()}`, coverageTone)}
      </div>
      <div class="answer-body">
        ${result.summary ? `<p class="answer-summary">${esc(result.summary)}</p>` : ''}
        <div class="prose">${markdownish(result.answer)}</div>
        ${result.coverage_note ? `<div class="coverage-note">${icon('info', 14)}<div><strong>Coverage.</strong> ${esc(result.coverage_note)}</div></div>` : ''}
        ${chartFor(result)}
        <div class="answer-meta">
          <span>${fmt(result.row_count)} rows retrieved</span>
          <span>${result.latency_ms} ms</span>
          <span>${result.provider_used ? (result.provider_online ? 'provider response' : 'provider fallback') : (result.provider_configured ? 'local SQL summary' : 'offline synthesizer')}</span>
        </div>
        ${ev.length ? `<div class="answer-actions">
          <button class="btn sm outline" data-action="toggle" data-id="${result.id}">Show evidence (${ev.length})</button>
          <button class="btn sm outline" data-action="csv" data-id="${result.id}">${icon('download', 13)} Export CSV</button>
        </div>
        <div class="evidence-slot" id="ev-${result.id}"></div>` : ''}
        ${result.sql ? `<details class="sql-block"><summary>${icon('chevron-right', 13)} Executed SQL</summary>
          <div class="sql-head"><span>read-only · row-capped</span><button class="btn sm ghost" data-action="copy" data-id="${result.id}">${icon('copy', 12)} Copy</button></div>
          <pre>${esc(result.sql)}</pre></details>` : ''}
        ${result.sources && result.sources.length ? `<div class="sources">Sources · ${esc(result.sources.slice(0, 6).join(' · '))}</div>` : ''}
      </div>
    </div>`
}

export async function mount(root) {
  root.innerHTML = `
    <div class="copilot">
      ${pageHead({
        eyebrow: 'Ask the record',
        title: 'Groundwater copilot',
        lede: 'Ask about levels, potability, extraction or one station. The answer cites the rows behind it, names its coverage limits and states its confidence.',
        actions: '<button class="btn ghost sm" id="clear-thread">' + icon('refresh', 13) + ' New thread</button>',
      })}
      <div id="copilot-error"></div>
      <div class="thread" id="chat" aria-live="polite"></div>
      <form class="composer" id="composer">
        <div class="composer-inner">
          <label class="sr-only" for="ask-input">Ask a groundwater question</label>
          <input id="ask-input" type="text" autocomplete="off" placeholder="Ask about levels, quality, extraction or a station…" />
          <button class="btn primary" id="ask-btn" type="submit">Ask</button>
        </div>
        <div class="composer-hint">
          <span>Enter to send · answers carry station-level evidence</span>
          <span id="composer-model">Offline synthesizer</span>
        </div>
      </form>
    </div>`

  const chat = root.querySelector('#chat')
  const err = root.querySelector('#copilot-error')
  const input = root.querySelector('#ask-input')
  const btn = root.querySelector('#ask-btn')
  const modelEl = root.querySelector('#composer-model')

  function paintModel() {
    const s = getSettings()
    modelEl.textContent = s.provider === 'offline' ? 'Offline synthesizer' : s.provider
  }
  paintModel()

  function render() {
    chat.innerHTML = messages.map((m) => {
      if (m.kind === 'user') return `<div class="msg-user">${esc(m.text)}</div>`
      if (m.kind === 'intro') {
        return `<div class="intro">
          <h2>Ask a question of the record</h2>
          <p>Answers are assembled from retrieved rows, then checked for coverage. Start with one of these, or ask about any station, district or parameter.</p>
          <div class="suggestions">
            ${SUGGESTIONS.map((s) => `<button class="suggestion" data-suggest="${esc(s)}"><span>${esc(s)}</span>${icon('arrow-right', 14)}</button>`).join('')}
          </div>
        </div>`
      }
      if (m.kind === 'notice') return `<div class="bubble-stopped" role="status">${esc(m.text)}</div>`
      return `<div class="msg-assistant">${answer(m.result)}</div>`
    }).join('') + (busy
      ? `<div class="bubble-busy"><span class="spinner" aria-hidden="true"></span> Retrieving evidence and checking coverage…</div>`
      : '')
    // The thread is replaced on every response. Re-run entry setup so newly
    // inserted answer cards become visible and their charts/counts can animate.
    enter(chat)
    btn.disabled = false
    btn.textContent = busy ? 'Stop' : 'Ask'
    btn.setAttribute('aria-label', busy ? 'Stop response generation' : 'Ask')
    if (messages.length > 1 || busy) {
      window.setTimeout(() => {
        const answers = chat.querySelectorAll('.msg-assistant')
        const last = answers[answers.length - 1]
        // Jump to the start of a finished answer; while waiting, keep the busy state in view.
        const top = !busy && last
          ? last.getBoundingClientRect().top + window.scrollY - 68
          : document.documentElement.scrollHeight
        window.scrollTo({ top, behavior: reducedMotion() ? 'auto' : 'smooth' })
      }, 20)
    }
  }

  async function send(text) {
    const query = String(text || input.value || '').trim()
    if (!query || busy) return
    input.value = ''
    err.innerHTML = ''
    busy = true
    if (messages.length === 1 && messages[0].kind === 'intro') messages = []
    messages.push({ kind: 'user', text: query })
    const controller = new AbortController()
    requestController = controller
    render()
    try {
      const result = await api.ask(query, getSettings(), { signal: controller.signal })
      result.id = ++seq
      messages.push({ kind: 'answer', result })
    } catch (e) {
      if (!controller.signal.aborted && e.name !== 'AbortError') err.innerHTML = errorNote(e.message)
    } finally {
      if (requestController === controller) {
        requestController = null
        busy = false
        render()
      }
    }
  }

  function stop() {
    if (!requestController) return
    requestController.abort()
    requestController = null
    busy = false
    messages.push({ kind: 'notice', text: 'Response stopped.' })
    render()
    input.focus()
  }

  root.querySelector('#clear-thread').addEventListener('click', () => {
    if (busy) return
    messages = [{ kind: 'intro' }]
    seq = 0
    err.innerHTML = ''
    render()
    window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' })
    input.focus()
  })

  chat.addEventListener('click', (e) => {
    const suggestion = e.target.closest('[data-suggest]')
    if (suggestion) { send(suggestion.dataset.suggest); return }
    const action = e.target.closest('[data-action]')
    if (!action) return
    const id = Number(action.dataset.id)
    const msg = messages.find((m) => m.result && m.result.id === id)
    if (!msg) return
    const result = msg.result
    if (action.dataset.action === 'csv') {
      downloadCsv('ingres_evidence.csv', result.evidence || [])
      return
    }
    if (action.dataset.action === 'toggle') {
      const slot = document.getElementById('ev-' + id)
      const ev = result.evidence || []
      if (!slot) return
      const open = slot.dataset.open === '1'
      slot.innerHTML = open ? '' : evidenceTable(ev)
      slot.dataset.open = open ? '0' : '1'
      action.textContent = open ? `Show evidence (${ev.length})` : 'Hide evidence'
      return
    }
    if (action.dataset.action === 'copy') {
      copyText(result.sql || '', 'SQL copied')
    }
  })

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  })
  root.querySelector('#composer').addEventListener('submit', (e) => {
    e.preventDefault()
    if (busy) stop()
    else send()
  })

  render()
}
