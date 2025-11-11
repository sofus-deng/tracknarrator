async function fetchSummary() {
  const status = document.getElementById('status');
  status.textContent = 'Loading demo/export/summary.json ...';
  try {
    const res = await fetch('../demo/export/summary.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    status.textContent = 'Loaded.';
    renderKPIs(data);
    renderCards(data.cards || []);
    renderLaps((data.sparklines && data.sparklines.laps) || []);
  } catch (e) {
    status.textContent = 'Not found. Run `make demo` then refresh.';
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