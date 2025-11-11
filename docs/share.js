function q(name) { return new URLSearchParams(location.search).get(name) }
async function fetchSummaryByToken(tok) {
  const status = document.getElementById('status'); status.textContent = 'Loading...'
  try {
    const res = await fetch(`../shared/${encodeURIComponent(tok)}/summary?ai_native=on`, { cache: 'no-store' })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const data = await res.json(); status.textContent = 'Loaded.'
    renderKPIs(data); renderCards(data.cards || []); renderLaps((data.sparklines && data.sparklines.laps) || [])
  } catch (e) { status.textContent = 'Invalid/expired token'; console.error(e) }
}
function renderKPIs(data) {
  const box = document.getElementById('kpis'); box.classList.remove('hidden');
  const k = (data.kpis || {}); const items = [['Total Laps', k.total_laps], ['Best Lap (ms)', k.best_lap_ms], ['Median Lap (ms)', k.median_lap_ms], ['Session Duration (ms)', k.session_duration_ms]]
  box.innerHTML = items.map(([k, v]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v ?? '-'}</div></div>`).join('')
}
function sevBadge(sev) { const s = Number(sev ?? 0).toFixed(2); return `<span class="badge">severity ${s}</span>` }
function renderCards(cards) {
  const root = document.getElementById('cards'); root.innerHTML = cards.map(c => `
  <article class="card"><div class="meta">${c.icon || '🏁'} ${c.type} • lap ${c.lap_no ?? '-'}</div>
  <h3 class="title">${c.title || '(untitled)'}</h3><div class="meta">${c.metric ?? ''}</div><div>${sevBadge(c.severity)}</div></article>`).join('')
}
function renderLaps(laps) {
  const root = document.getElementById('laps'); if (!Array.isArray(laps) || laps.length === 0) { root.innerHTML = '<span class="muted">No laps.</span>'; return }
  const rows = laps.slice(0, 500).map(r => `<tr><td>${r.lap_no ?? ''}</td><td>${r.lap_ms ?? ''}</td></tr>`).join('')
  root.innerHTML = `<table><thead><tr><th>Lap</th><th>Lap (ms)</th></tr></thead><tbody>${rows}</tbody></table>`
}
document.getElementById('loadBtn').addEventListener('click', () => { const t = document.getElementById('tok').value.trim(); if (t) fetchSummaryByToken(t) })
const initial = q('token'); if (initial) { document.getElementById('tok').value = initial; fetchSummaryByToken(initial) }