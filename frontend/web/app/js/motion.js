// Shared motion: viewport reveals, count-ups and chart triggers.
// Motion is opt-in through [data-motion-el], [data-count-to] and .motion-visual,
// and every path bows out when the operating system asks for reduced motion.

const reduce = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/* selector, base delay, stagger between matches */
const REVEAL_GROUPS = [
  ['.page-head', 0, 0],
  ['.record-item', 0, 45],
  ['.quality-card', 40, 30],
  ['.suggestion', 60, 30],
  ['.panel', 40, 55],
  ['.method-strip', 180, 0],
  ['.intro', 0, 0],
  ['.answer', 0, 0],
  ['.audit-summary', 0, 0],
]

const VISUAL_SELECTOR = '.chart, .donut-wrap, .mini-bars, .split-bar, .health-line'

let countIO = null
let visualIO = null
const countRunIds = new WeakMap()

function countObserver() {
  if (!countIO) {
    countIO = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        countIO.unobserve(entry.target)
        runCount(entry.target, Number(entry.target.dataset.shineDelayMs || 250))
      })
    }, { threshold: 0.5, rootMargin: '0px 0px -4% 0px' })
  }
  return countIO
}

function visualObserver() {
  if (!visualIO) {
    visualIO = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('in')
        if (!reduce()) syncMotionAnimations(entry.target, true)
        visualIO.unobserve(entry.target)
      })
    }, { threshold: 0.18, rootMargin: '0px 0px -4% 0px' })
  }
  return visualIO
}

function syncMotionAnimations(el, startVisible = false) {
  el.querySelectorAll('[data-motion-animate]').forEach((animation) => {
    const themeMismatch = animation.dataset.motionTheme && animation.dataset.motionTheme !== document.documentElement.dataset.theme
    try {
      if (themeMismatch) {
        if (animation.dataset.motionRunning === '1') animation.endElement()
        delete animation.dataset.motionRunning
      } else if (startVisible) {
        animation.beginElement()
        animation.dataset.motionRunning = '1'
      }
    } catch (e) {}
  })
}

function replayVisual(el) {
  el.classList.remove('in')
  el.classList.add('motion-visual')
  if (!reduce()) syncMotionAnimations(el)
  visualObserver().observe(el)
}

function formatCount(value, el) {
  const decimals = Number(el.dataset.countDecimals || 0)
  const group = el.dataset.countGroup !== 'false'
  const n = Number(value)
  const rendered = group
    ? n.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : n.toFixed(decimals)
  return (el.dataset.countPrefix || '') + rendered + (el.dataset.countSuffix || '')
}

function runCount(el, shineDelayMs = 250) {
  const to = Number(el.dataset.countTo)
  if (!Number.isFinite(to)) return
  const runId = (countRunIds.get(el) || 0) + 1
  countRunIds.set(el, runId)
  if (reduce()) {
    el.textContent = formatCount(to, el)
    return
  }
  const duration = Number(el.dataset.countDuration || 900)
  const started = performance.now()
  const tick = (now) => {
    if (!el.isConnected || countRunIds.get(el) !== runId) return
    const t = Math.min(1, (now - started) / duration)
    const eased = 1 - Math.pow(1 - t, 4)
    el.textContent = formatCount(to * eased, el)
    if (t < 1) requestAnimationFrame(tick)
    else {
      el.textContent = formatCount(to, el)
      el.classList.remove('count-shine')
      el.style.setProperty('--shine-delay', `${shineDelayMs}ms`)
      void el.offsetWidth
      el.classList.add('count-shine')
    }
  }
  requestAnimationFrame(tick)
}

function prepareCount(el) {
  if (el.dataset.countBound === '1') return
  el.dataset.countBound = '1'
  const to = Number(el.dataset.countTo)
  if (!Number.isFinite(to)) return
  if (reduce()) {
    el.textContent = formatCount(to, el)
    return
  }
  // Start low so the observer's count is the visible movement.
  el.textContent = formatCount(0, el)
  countObserver().observe(el)
}

function all(root, selector) {
  const nodes = Array.from(root.querySelectorAll(selector))
  if (root.matches && root.matches(selector)) nodes.unshift(root)
  return nodes
}

function isInViewport(el) {
  const rect = el.getBoundingClientRect()
  return rect.bottom > 0 && rect.top < window.innerHeight
}

export function enter(root) {
  if (!root || !root.querySelectorAll) return
  if (reduce()) {
    all(root, '[data-count-to]').forEach((el) => {
      el.textContent = formatCount(Number(el.dataset.countTo), el)
    })
    all(root, VISUAL_SELECTOR).forEach((el) => el.classList.add('in'))
    return
  }

  document.documentElement.dataset.motion = 'on'
  const claimed = new Set()

  REVEAL_GROUPS.forEach(([selector, base, step]) => {
    let index = 0
    all(root, selector).forEach((el) => {
      if (claimed.has(el) || el.dataset.motionEl === '1') return
      claimed.add(el)
      el.dataset.motionEl = '1'
      const delay = base + index * step
      if (delay) el.style.setProperty('--reveal-delay', `${delay}ms`)
      // Cards settle into their final layout on page entry, not as scroll-linked
      // fades. Only data and chart marks below wait for their viewport moment.
      requestAnimationFrame(() => {
        if (el.isConnected) el.classList.add('is-in')
      })
      index += 1
    })
  })

  all(root, '[data-count-to]').forEach(prepareCount)

  all(root, VISUAL_SELECTOR).forEach((el) => {
    if (el.dataset.motionVisual === '1') return
    el.dataset.motionVisual = '1'
    el.classList.add('motion-visual')
    visualObserver().observe(el)
  })
}

export function replayCounts(root, { shineDelayMs = 100 } = {}) {
  if (!root || !root.querySelectorAll) return
  all(root, '[data-count-to]').forEach((el) => {
    el.dataset.countBound = '1'
    countRunIds.set(el, (countRunIds.get(el) || 0) + 1)
    el.classList.remove('count-shine')
    el.dataset.shineDelayMs = String(shineDelayMs)
    el.textContent = formatCount(0, el)
    if (countIO) countIO.unobserve(el)
    if (reduce() || isInViewport(el)) runCount(el, shineDelayMs)
    else countObserver().observe(el)
  })

}

export function replayVisuals(root) {
  if (!root || !root.querySelectorAll) return
  all(root, VISUAL_SELECTOR).forEach(replayVisual)
  const records = all(root, '.record-item')
  if (!reduce() && records.length) {
    root.removeAttribute('data-theme-replay')
    requestAnimationFrame(() => {
      if (!root.isConnected) return
      root.setAttribute('data-theme-replay', '1')
      window.setTimeout(() => root.removeAttribute('data-theme-replay'), 900)
    })
  }
}
