(function () {
  const qs = new URLSearchParams(location.search);
  const $ = (id) => document.getElementById(id);
  const apiInput = $('apiBase'), saveBtn = $('saveApi'), hint = $('apiHint');
  const fileEl = $('file'), drop = $('drop'), go = $('go'), stat = $('stat');
  const out = $('result'), sid = $('sid'), tok = $('tok'), apiLink = $('apiLink'), viewerLink = $('viewerLink');

  function getAPI() {
    return qs.get('api') || localStorage.getItem('tn_api') || $('apiBase').placeholder;
  }
  function setAPI(v) { localStorage.setItem('tn_api', v); }
  function fmt(s) { return (s == null ? '' : String(s)); }

  function init() {
    const base = getAPI();
    apiInput.value = base;
    hint.textContent = "using " + base;
    ;['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.style.borderColor = '#64d2ff' }));
    ;['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.style.borderColor = '#3a485a' }));
    drop.addEventListener('drop', (e) => { e.preventDefault(); if (e.dataTransfer.files?.length) { fileEl.files = e.dataTransfer.files; } });
    saveBtn.onclick = () => { setAPI(apiInput.value.trim()); hint.textContent = "using " + getAPI(); };
    go.onclick = uploadAndShare;
  }

  async function uploadAndShare() {
    try {
      const base = getAPI();
      if (!fileEl.files || !fileEl.files[0]) { stat.textContent = "Please choose a file."; return; }
      stat.textContent = "Uploading…";
      const fd = new FormData(); fd.append('file', fileEl.files[0]);
      const up = await fetch(base + '/upload', { method: 'POST', body: fd });
      if (!up.ok) { throw new Error('upload failed ' + up.status); }
      const u = await up.json();
      const sessionId = u.session_id || u.id || u.session || 'unknown';
      sid.textContent = sessionId;

      stat.textContent = "Creating share…";
      const create = await fetch(`${base}/share/${encodeURIComponent(sessionId)}?ttl_s=3600&label=web`, { method: 'POST' });
      if (!create.ok) { throw new Error('share failed ' + create.status); }
      const cj = await create.json();
      const token = cj.token; tok.textContent = token;

      apiLink.href = `${base}/shared/${encodeURIComponent(token)}/summary`;
      viewerLink.href = `./share.html?token=${encodeURIComponent(token)}`;
      out.style.display = 'block';
      stat.textContent = "Done.";
    } catch (err) {
      console.error(err); stat.textContent = "Error: " + fmt(err.message || err);
    }
  }
  init();
})();