const KEY = 'ingres-settings'

export const DEFAULT_SETTINGS = {
  provider: 'offline',
  apiKey: '',
  model: '',
  baseUrl: '',
}

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS }
  } catch (e) {
    return { ...DEFAULT_SETTINGS }
  }
}

let current = load()
const listeners = new Set()

export function getSettings() {
  return { ...current }
}

export function saveSettings(next) {
  current = { ...DEFAULT_SETTINGS, ...next }
  try { localStorage.setItem(KEY, JSON.stringify(current)) } catch (e) {}
  listeners.forEach((fn) => fn(getSettings()))
}

export function onSettings(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function providerLabel(settings) {
  switch (settings.provider) {
    case 'openrouter': return 'OpenRouter'
    case 'gemini': return 'Google Gemini'
    case 'openai': return 'OpenAI'
    case 'custom': return 'Custom endpoint'
    default: return 'Offline synthesizer'
  }
}
let pendingStation = null

export function setPendingStation(value) {
  pendingStation = value
}

export function takePendingStation() {
  const value = pendingStation
  pendingStation = null
  return value
}
