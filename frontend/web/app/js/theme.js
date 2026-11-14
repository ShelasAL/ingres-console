// Theme preference: system, dark or light. Persisted in localStorage and
// mirrored onto <html> so CSS tokens resolve before the first paint.

const KEY = 'ingres-theme'
const VALID = new Set(['system', 'dark', 'light'])
const mql = window.matchMedia('(prefers-color-scheme: light)')

let preference = 'system'
try {
  const saved = localStorage.getItem(KEY)
  if (VALID.has(saved)) preference = saved
} catch (e) {}

const listeners = new Set()

const resolve = () => (preference === 'system' ? (mql.matches ? 'light' : 'dark') : preference)

export function getThemePref() {
  return preference
}

export function getResolvedTheme() {
  return resolve()
}

export function applyTheme(next = preference, persist = true) {
  if (VALID.has(next)) preference = next
  if (persist) {
    try { localStorage.setItem(KEY, preference) } catch (e) {}
  }
  const resolved = resolve()
  const root = document.documentElement
  root.dataset.theme = resolved
  root.dataset.themePref = preference
  root.style.colorScheme = resolved
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', resolved === 'light' ? '#eee8dc' : '#090a12')
  listeners.forEach((fn) => fn(resolved, preference))
  return resolved
}

export function setTheme(next) {
  return applyTheme(next, true)
}

export function toggleTheme() {
  return applyTheme(resolve() === 'light' ? 'dark' : 'light', true)
}

export function onTheme(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

mql.addEventListener('change', () => {
  if (preference === 'system') applyTheme('system', false)
})
