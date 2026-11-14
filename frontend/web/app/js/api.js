async function request(path, options = {}) {
  const res = await fetch(path, options)
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch (e) { data = { error: text } }
  if (!res.ok) throw new Error((data && data.error) || 'Request failed with ' + res.status)
  return data
}

export const api = {
  health: () => request('/api/health'),
  summary: () => request('/api/summary'),
  states: () => request('/api/states'),
  districts: (state) => request('/api/districts?state=' + encodeURIComponent(state)),
  stations: (district) => request('/api/stations?district=' + encodeURIComponent(district)),
  station: (wellId) => request('/api/station/' + encodeURIComponent(wellId)),
  mapStations: (state) =>
    request('/api/map/stations' + (state ? '?state=' + encodeURIComponent(state) : '')),
  explore: (table, state) =>
    request('/api/explore?table=' + table + (state ? '&state=' + encodeURIComponent(state) : '')),
  performance: () => request('/api/performance'),
  ask: (query, settings, options = {}) =>
    request('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: options.signal,
      body: JSON.stringify({
        query,
        provider: settings.provider === 'offline' ? '' : settings.provider,
        api_key: settings.apiKey || '',
        model: settings.model || '',
        base_url: settings.baseUrl || '',
      }),
    }),
}

export function downloadCsv(filename, rows) {
  if (!rows || !rows.length) return
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))))
  const esc = (v) => {
    if (v === null || v === undefined) return ''
    const s = String(v)
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
  }
  const csv = [keys.join(','), ...rows.map((r) => keys.map((k) => esc(r[k])).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
