// Helper functions for static JSON loading with fallback paths
async function fetchStaticJson(primaryPath, fallbackPath) {
  try {
    const res = await fetch(primaryPath, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn(`Failed to fetch ${primaryPath}, trying fallback`);
  }

  try {
    const res = await fetch(fallbackPath, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn(`Failed to fetch fallback ${fallbackPath}`);
  }

  throw new Error(`Could not load data from ${primaryPath} or ${fallbackPath}`);
}

// Global variables to store loaded data
window.tnSummary = null;
window.tnViz = null;
window.tnCoachScore = null;

// Toast notification system
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.style.display = 'block';

  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

async function fetchSummary() {
  try {
    // Try primary path first, then fallback
    const data = await fetchStaticJson('data/summary.json', 'demo/export/summary.json');
    window.tnSummary = data; // Store globally for reuse
    showToast('Demo session loaded.');
    renderKPIs(data);
    renderCards(data.cards || []);
    renderLaps((data.sparklines && data.sparklines.laps) || []);
    renderEvents(data.events || []);
  } catch (e) {
    showToast('Demo data could not be loaded. Please try again later or contact the maintainer.');
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
  if (!Array.isArray(laps) || laps.length === 0) {
    root.innerHTML = '<span class="muted">No laps are available in this demo session.</span>';
    return;
  }
  const rows = laps.slice(0, 500).map(r => `<tr><td>${r.lap_no ?? ''}</td><td>${r.lap_ms ?? ''}</td></tr>`).join('');
  root.innerHTML = `<table><thead><tr><th>Lap</th><th>Lap (ms)</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderEvents(events) {
  const root = document.getElementById('cards');
  if (!Array.isArray(events) || events.length === 0) {
    root.innerHTML = '<span class="muted">No key events were flagged for this session.</span>';
    return;
  }
  // For now, render events using the same card layout
  root.innerHTML = events.map(e => `
    <article class="card">
      <div class="meta">${e.icon || '🏁'} ${e.type || 'Event'} • lap ${e.lap_no ?? '-'}</div>
      <h3 class="title">${e.title || e.description || '(untitled)'}</h3>
      <div class="meta">${e.metric || ''}</div>
    </article>
  `).join('');
}
document.getElementById('loadBtn')?.addEventListener('click', fetchSummary);

// Share functionality
async function createShareLink() {
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

    showToast('Share link created!');
  } catch (e) {
    showToast('Failed to create share link');
    console.error(e);
  }
}

function copyShareUrl() {
  const shareUrl = document.getElementById('shareUrl');
  shareUrl.select();
  document.execCommand('copy');
  showToast('Share link copied to clipboard.');
}

document.getElementById('shareBtn')?.addEventListener('click', createShareLink);
document.getElementById('copyBtn')?.addEventListener('click', copyShareUrl);

// Language and visualization functions
// Multi-language UI is planned for future versions; the hosted demo currently defaults to English.
function getLang() { return 'en'; }
async function fetchViz() {
  // const status = document.getElementById('status');
  // status.textContent = 'Loading lap time analysis...';
  try {
    // Try to load from static files
    let vizData = null;

    // First check if we already have viz data
    if (window.tnViz) {
      vizData = window.tnViz;
    } else {
      // Try to load from static files
      try {
        vizData = await fetchStaticJson('data/viz.json', 'demo/export/viz.json');
        window.tnViz = vizData; // Store globally
      } catch (e) {
        // If viz.json doesn't exist, try to derive from summary data
        if (window.tnSummary && window.tnSummary.sparklines && window.tnSummary.sparklines.laps_ms) {
          // Create a simple viz structure from summary data
          const lapsMs = window.tnSummary.sparklines.laps_ms;
          const medianLap = window.tnSummary.kpis && window.tnSummary.kpis.median_lap_ms;

          if (medianLap && lapsMs.length > 0) {
            vizData = {
              lap_delta_series: lapsMs.map((lapMs, index) => ({
                lap_no: index + 1,
                delta_ms_to_median: lapMs - medianLap,
                delta_ma3: 0 // Simple moving average would need more calculation
              }))
            };
            window.tnViz = vizData;
          }
        }
      }
    }

    if (vizData && vizData.lap_delta_series) {
      drawLapChart(vizData.lap_delta_series);
      showToast('Lap time analysis loaded.');
    } else {
      showToast('Lap time analysis not available for this demo.');
    }
  } catch (e) {
    showToast('Could not load lap time analysis.');
    console.error(e);
  }
}
function drawLapChart(series) {
  const cv = document.getElementById('lapChart'); if (!cv || !series.length) return;
  const ctx = cv.getContext('2d'); ctx.clearRect(0, 0, cv.width, cv.height);
  const W = cv.width, H = cv.height, pad = 28;
  const xs = series.map(d => d.lap_no), ys = series.map(d => d.delta_ms_to_median);
  let minY = Math.min(...ys), maxY = Math.max(...ys);

  // Ensure zero is always visible in the chart
  const range = maxY - minY;
  const padding = range * 0.1; // Add 10% padding
  if (minY > 0) minY = -padding;
  if (maxY < 0) maxY = padding;

  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const x = (v) => pad + (W - 2 * pad) * (v - xMin) / (xMax - xMin || 1);
  const y = (v) => H - pad - (H - 2 * pad) * (v - minY) / ((maxY - minY) || 1);

  // axes
  ctx.strokeStyle = "#243040"; ctx.beginPath(); ctx.moveTo(pad, H - pad); ctx.lineTo(W - pad, H - pad); ctx.moveTo(pad, pad); ctx.lineTo(pad, H - pad); ctx.stroke();

  // zero baseline - always visible and more prominent
  ctx.strokeStyle = "#666666"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(pad, y(0)); ctx.lineTo(W - pad, y(0)); ctx.stroke(); ctx.lineWidth = 1;

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
  const coachMeta = document.getElementById('coachMeta');

  try {
    // First check if we already have coach score data
    if (window.tnCoachScore) {
      drawCoachGauge(window.tnCoachScore);
      showToast('Coach assessment loaded.');
      return;
    }

    // Try to load from static files
    let data = null;
    try {
      data = await fetchStaticJson('data/coach_score.json', 'demo/export/coach_score.json');
      window.tnCoachScore = data; // Store globally
      drawCoachGauge(data);
      showToast('Coach assessment loaded.');
    } catch (e) {
      // Show friendly message if coach score is not available
      coachMeta.textContent = 'Coach assessment is not available in this demo.';
      showToast('Coach assessment not available.');
      console.error(e);
    }
  } catch (e) {
    coachMeta.textContent = 'Coach assessment is not available in this demo.';
    showToast('Could not load coach assessment.');
    console.error(e);
  }
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