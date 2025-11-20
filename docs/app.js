async function fetchSummary() {
  const status = document.getElementById('status');
  status.textContent = 'Loading demo data...';
  try {
    const res = await fetch('demo/export/summary.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    status.textContent = 'Loaded.';
    renderKPIs(data);
    renderCards(data.cards || []);
    renderLaps((data.sparklines && data.sparklines.laps) || []);
  } catch (e) {
    status.textContent = 'Demo data could not be loaded. Please try again later or contact the maintainer.';
    console.error(e);
  }
}
function renderKPIs(data) {
  const box = document.getElementById('kpis'); box.classList.remove('hidden');
  const k = (data.kpis || {});
  const items = [
    ['Total Laps', k.total_laps],
    ['Best Lap (ms)', k.best_lap_ms],
    ['Median Lap (ms)', k.median_lap_ms],
    ['Session Duration (ms)', k.session_duration_ms]
  ];
  box.innerHTML = items.map(([k, v]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v ?? '-'}</div></div>`).join('');
}
function sevBadge(sev) {
  const s = Number(sev ?? 0).toFixed(2);
  return `<span class="badge">severity ${s}</span>`;
}
function renderCards(cards) {
  const root = document.getElementById('cards');
  root.innerHTML = cards.map(c => `
    <article class="card">
      <div class="meta">${c.icon || '🏁'} ${c.type} • lap ${c.lap_no ?? '-'}</div>
      <h3 class="title">${c.title || '(untitled)'}</h3>
      <div class="meta">${c.metric ?? ''}</div>
      <div>${sevBadge(c.severity)}</div>
    </article>
  `).join('');
}
function renderLaps(laps) {
  const root = document.getElementById('laps');
  if (!Array.isArray(laps) || laps.length === 0) { root.innerHTML = '<span class="muted">No laps. Run demo.</span>'; return; }
  const rows = laps.slice(0, 500).map(r => `<tr><td>${r.lap_no ?? ''}</td><td>${r.lap_ms ?? ''}</td></tr>`).join('');
  root.innerHTML = `<table><thead><tr><th>Lap</th><th>Lap (ms)</th></tr></thead><tbody>${rows}</tbody></table>`;
}
document.getElementById('loadBtn').addEventListener('click', fetchSummary);

// Share functionality
async function createShareLink() {
  const status = document.getElementById('status');
  status.textContent = 'Creating share link...';

  try {
    // For demo purposes, use the barber session ID
    const sessionId = 'barber-demo-r1';

    // Create share token
    const res = await fetch(`../share/${sessionId}`, { method: 'POST' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    // Show share result
    const shareResult = document.getElementById('shareResult');
    const shareUrl = document.getElementById('shareUrl');
    shareUrl.value = `${window.location.origin}/docs/share.html?token=${data.token}`;
    shareResult.classList.remove('hidden');

    status.textContent = 'Share link created!';
  } catch (e) {
    status.textContent = 'Failed to create share link';
    console.error(e);
  }
}

function copyShareUrl() {
  const shareUrl = document.getElementById('shareUrl');
  shareUrl.select();
  document.execCommand('copy');

  const copyBtn = document.getElementById('copyBtn');
  const originalText = copyBtn.textContent;
  copyBtn.textContent = 'Copied!';
  setTimeout(() => {
    copyBtn.textContent = originalText;
  }, 2000);
}

document.getElementById('shareBtn').addEventListener('click', createShareLink);
document.getElementById('copyBtn').addEventListener('click', copyShareUrl);

// Language and visualization functions
// Multi-language UI is planned for future versions; the hosted demo currently defaults to English.
function getLang() { return 'en'; }
async function fetchViz() {
  try {
    // Try to infer session id from the already loaded summary.json path. Fallback: call /sessions to get latest.
    const res = await fetch('../sessions'); // backend served locally during demo
    const sessions = res.ok ? await res.json() : [];
    const sid = sessions && sessions.length ? sessions[0].session_id : null;
    if (!sid) throw new Error('No session');
    const v = await (await fetch(`../session/${encodeURIComponent(sid)}/viz`, { cache: 'no-store' })).json();
    drawLapChart(v.lap_delta_series || []);
  } catch (e) { console.error(e); }
}
function drawLapChart(series) {
  const cv = document.getElementById('lapChart'); if (!cv || !series.length) return;
  const ctx = cv.getContext('2d'); ctx.clearRect(0, 0, cv.width, cv.height);
  const W = cv.width, H = cv.height, pad = 28;
  const xs = series.map(d => d.lap_no), ys = series.map(d => d.delta_ms_to_median);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const x = (v) => pad + (W - 2 * pad) * (v - xMin) / (xMax - xMin || 1);
  const y = (v) => H - pad - (H - 2 * pad) * (v - minY) / ((maxY - minY) || 1);
  // axes
  ctx.strokeStyle = "#243040"; ctx.beginPath(); ctx.moveTo(pad, H - pad); ctx.lineTo(W - pad, H - pad); ctx.moveTo(pad, pad); ctx.lineTo(pad, H - pad); ctx.stroke();
  // zero line
  if (minY < 0 && maxY > 0) { ctx.strokeStyle = "#3a485a"; ctx.beginPath(); ctx.moveTo(pad, y(0)); ctx.lineTo(W - pad, y(0)); ctx.stroke(); }
  // line
  ctx.strokeStyle = "#64d2ff"; ctx.beginPath();
  series.forEach((d, i) => { const xx = x(d.lap_no), yy = y(d.delta_ms_to_median); i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); });
  ctx.stroke();
  // moving average
  ctx.strokeStyle = "#9ad46a"; ctx.beginPath();
  series.forEach((d, i) => { const xx = x(d.lap_no), yy = y(d.delta_ma3); i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); });
  ctx.stroke();
}
document.getElementById('vizBtn')?.addEventListener('click', fetchViz);

function qs() { return new URLSearchParams(location.search); }
async function loadSummaryAuto() {
  try {
    const p = qs();
    if (p.get('token')) {
      const t = p.get('token');
      const r = await fetch(`../shared/${encodeURIComponent(t)}/summary?ai_native=off&lang=${getLang()}`, { cache: 'no-store' });
      if (!r.ok) throw new Error('shared fetch ' + r.status);
      return await r.json();
    }
    if (p.get('sid')) {
      const sid = p.get('sid');
      const r = await fetch(`../session/${encodeURIComponent(sid)}/summary?ai_native=off&lang=${getLang()}`, { cache: 'no-store' });
      if (!r.ok) throw new Error('api fetch ' + r.status);
      return await r.json();
    }
    // default: demo mode
    const r = await fetch('demo/export/summary.json', { cache: 'no-store' });
    if (!r.ok) throw new Error('demo fetch ' + r.status);
    return await r.json();
  } catch (e) { console.error(e); return { events: [], cards: [], sparklines: {} }; }
}
// if page already had an init flow, keep it. Otherwise expose a helper:
window.__tn_loadSummaryAuto = loadSummaryAuto;

async function fetchCoach() {
  try {
    // Prefer live API sid if available; else demo file
    const res = await fetch('../sessions'); // may fail on static; tolerate
    let sid = null;
    if (res.ok) { const arr = await res.json(); if (Array.isArray(arr) && arr.length) sid = arr[0].session_id; }
    let data = null;
    if (sid) {
      const r = await fetch(`../session/${encodeURIComponent(sid)}/coach?lang=${getLang()}`, { cache: 'no-store' });
      data = r.ok ? await r.json() : null;
    }
    if (!data) {
      const r = await fetch('demo/export/coach_score.json', { cache: 'no-store' });
      data = r.ok ? await r.json() : null;
    }
    if (data) { drawCoachGauge(data); }
  } catch (e) { console.error(e); }
}
function drawCoachGauge(cs) {
  const cv = document.getElementById('coachGauge'); if (!cv) return;
  const ctx = cv.getContext('2d'); const W = cv.width, H = cv.height; ctx.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H - 10, r = Math.min(W, H * 1.8) / 2 - 14;
  // arc background
  ctx.lineWidth = 16; ctx.strokeStyle = "#243040"; ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI); ctx.stroke();
  // value arc
  const v = Math.max(0, Math.min(100, Number(cs.total_score || 0)));
  const ang = Math.PI + (v / 100) * Math.PI;
  ctx.strokeStyle = "#64d2ff"; ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, ang); ctx.stroke();
  // text
  ctx.fillStyle = "#e6f2ff"; ctx.font = "28px system-ui, sans-serif"; ctx.textAlign = "center";
  ctx.fillText(String(v), cx, cy - 10);
  const meta = document.getElementById('coachMeta');
  const badge = cs.badge || '-';
  meta.textContent = `badge: ${badge}`;
}
document.getElementById('coachBtn')?.addEventListener('click', fetchCoach);