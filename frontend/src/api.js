export async function api(path, opts = {}) {
  const r = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!r.ok) {
    let payload = null
    try { const j = await r.json(); payload = j.detail ?? j } catch {}
    const msg = typeof payload === 'string' ? payload : payload ? JSON.stringify(payload) : r.statusText
    const e = new Error(msg)
    e.detail = payload && typeof payload === 'object' ? payload : null
    throw e
  }
  if (r.status === 204) return null
  return r.json()
}
