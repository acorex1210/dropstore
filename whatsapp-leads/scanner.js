// ========================================================
// WhatsApp Leads Scanner - Script de consola
// Pegar en la consola de https://web.whatsapp.com
// ========================================================

(function() {
  const CONFIG = {
    keywords: [
      { keyword: 'novuma', campaign: 'Novuma' },
      { keyword: 'ellanse', campaign: 'Ellanse' },
      { keyword: 'botox', campaign: 'Botox' },
      { keyword: 'acido hialuronico', campaign: 'Acido Hialuronico' },
      { keyword: 'radiesse', campaign: 'Radiesse' },
      { keyword: 'bichectomia', campaign: 'Bichectomia' },
      { keyword: 'lipolaser', campaign: 'Lipolaser' },
      { keyword: 'hilos tensores', campaign: 'Hilos Tensores' },
      { keyword: 'plasma', campaign: 'Plasma' },
      { keyword: 'mesoterapia', campaign: 'Mesoterapia' }
    ],
    maxChats: 100,
    clickDelay: 600
  };

  let panel = null;

  function createPanel() {
    if (panel) panel.remove();

    panel = document.createElement('div');
    panel.id = 'wl-panel';
    panel.innerHTML = `
      <style>
        #wl-panel {
          position: fixed;
          top: 10px;
          right: 10px;
          width: 360px;
          max-height: 90vh;
          background: #111b21;
          border: 1px solid #2a3942;
          border-radius: 12px;
          z-index: 999999;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          color: #e9edef;
          box-shadow: 0 8px 32px rgba(0,0,0,0.4);
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        #wl-panel * { box-sizing: border-box; margin: 0; padding: 0; }
        #wl-header {
          background: #00a884;
          padding: 12px 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: move;
        }
        #wl-header h3 { font-size: 14px; font-weight: 600; }
        #wl-close {
          background: none; border: none; color: white;
          font-size: 18px; cursor: pointer; padding: 0 4px;
        }
        #wl-body {
          padding: 12px 16px;
          overflow-y: auto;
          flex: 1;
        }
        #wl-body label {
          display: block;
          font-size: 11px;
          color: #8696a0;
          margin-bottom: 4px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        #wl-body textarea, #wl-body input[type="text"] {
          width: 100%;
          background: #2a3942;
          border: 1px solid #3b4a54;
          color: #e9edef;
          border-radius: 6px;
          padding: 8px 10px;
          font-size: 12px;
          font-family: inherit;
          resize: vertical;
          outline: none;
          margin-bottom: 10px;
        }
        #wl-body textarea:focus, #wl-body input:focus {
          border-color: #00a884;
        }
        #wl-keywords-list {
          max-height: 120px;
          overflow-y: auto;
          margin-bottom: 10px;
        }
        .wl-kw-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px 8px;
          background: #2a3942;
          border-radius: 4px;
          margin-bottom: 3px;
          font-size: 11px;
        }
        .wl-kw-item .wl-camp { color: #00a884; }
        .wl-kw-item button {
          background: none; border: none; color: #ea4335;
          cursor: pointer; font-size: 12px; padding: 2px 4px;
        }
        .wl-btn-row { display: flex; gap: 6px; margin-bottom: 10px; }
        .wl-btn {
          flex: 1;
          padding: 8px 12px;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: all 0.2s;
        }
        .wl-btn-green { background: #00a884; color: white; }
        .wl-btn-green:hover { background: #06cf9c; }
        .wl-btn-blue { background: #53bdeb; color: white; }
        .wl-btn-blue:hover { background: #6dc4f0; }
        .wl-btn-gray { background: #2a3942; color: #e9edef; }
        .wl-btn-gray:hover { background: #3b4a54; }
        .wl-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        #wl-results {
          background: #2a3942;
          border-radius: 6px;
          padding: 8px;
          font-size: 11px;
          max-height: 200px;
          overflow-y: auto;
          display: none;
        }
        #wl-results.active { display: block; }
        .wl-result-item {
          padding: 4px 0;
          border-bottom: 1px solid #3b4a54;
        }
        .wl-result-item:last-child { border-bottom: none; }
        .wl-result-num { color: #e9edef; font-weight: 500; }
        .wl-result-camp { color: #00a884; font-size: 10px; }
        .wl-result-msg { color: #8696a0; font-size: 10px; margin-top: 2px; }
        #wl-status {
          padding: 6px 8px;
          font-size: 11px;
          text-align: center;
          border-radius: 4px;
          margin-top: 8px;
          display: none;
        }
        #wl-status.active { display: block; }
        #wl-status.info { background: rgba(134,150,160,0.15); color: #8696a0; }
        #wl-status.success { background: rgba(0,168,132,0.15); color: #00a884; }
        #wl-status.error { background: rgba(234,67,53,0.15); color: #ea4335; }
        #wl-add-row { display: flex; gap: 6px; margin-bottom: 10px; }
        #wl-add-row input { flex: 1; margin-bottom: 0; }
        #wl-add-row .wl-btn { flex: 0 0 auto; padding: 8px 12px; }
      </style>
      <div id="wl-header">
        <h3>WhatsApp Leads Scanner</h3>
        <button id="wl-close">&times;</button>
      </div>
      <div id="wl-body">
        <label>Palabras clave (formato: palabra → campaña)</label>
        <div id="wl-keywords-list"></div>
        <div id="wl-add-row">
          <input type="text" id="wl-new-kw" placeholder="Palabra clave">
          <input type="text" id="wl-new-camp" placeholder="Campaña">
          <button class="wl-btn wl-btn-green" id="wl-btn-add">+</button>
        </div>

        <div class="wl-btn-row">
          <button class="wl-btn wl-btn-green" id="wl-btn-scan">Escanear chats</button>
        </div>
        <div class="wl-btn-row">
          <button class="wl-btn wl-btn-blue" id="wl-btn-copy">Copiar al portapapeles</button>
          <button class="wl-btn wl-btn-gray" id="wl-btn-csv">CSV</button>
          <button class="wl-btn wl-btn-gray" id="wl-btn-json">JSON</button>
        </div>

        <div id="wl-results"></div>
        <div id="wl-status"></div>
      </div>
    `;

    document.body.appendChild(panel);
    setupEvents();
    renderKeywords();
  }

  function setupEvents() {
    document.getElementById('wl-close').onclick = () => panel.remove();

    const header = document.getElementById('wl-header');
    let dragging = false, offsetX, offsetY;
    header.onmousedown = (e) => {
      dragging = true;
      offsetX = e.clientX - panel.getBoundingClientRect().left;
      offsetY = e.clientY - panel.getBoundingClientRect().top;
      e.preventDefault();
    };
    document.onmousemove = (e) => {
      if (!dragging) return;
      panel.style.left = (e.clientX - offsetX) + 'px';
      panel.style.right = 'auto';
      panel.style.top = (e.clientY - offsetY) + 'px';
    };
    document.onmouseup = () => dragging = false;

    document.getElementById('wl-btn-add').onclick = addKeyword;
    document.getElementById('wl-btn-scan').onclick = startScan;
    document.getElementById('wl-btn-copy').onclick = copyToClipboard;
    document.getElementById('wl-btn-csv').onclick = downloadCSV;
    document.getElementById('wl-btn-json').onclick = downloadJSON;

    document.getElementById('wl-new-kw').onkeydown = (e) => {
      if (e.key === 'Enter') addKeyword();
    };
  }

  function renderKeywords() {
    const list = document.getElementById('wl-keywords-list');
    list.innerHTML = CONFIG.keywords.map((kw, i) => `
      <div class="wl-kw-item">
        <span>${kw.keyword} <span class="wl-camp">→ ${kw.campaign}</span></span>
        <button onclick="document.getElementById('wl-panel').__removeKw(${i})">✕</button>
      </div>
    `).join('');

    panel.__removeKw = (i) => {
      CONFIG.keywords.splice(i, 1);
      renderKeywords();
    };
  }

  function addKeyword() {
    const kwInput = document.getElementById('wl-new-kw');
    const campInput = document.getElementById('wl-new-camp');
    const kw = kwInput.value.trim();
    const camp = campInput.value.trim();
    if (!kw || !camp) return;
    if (CONFIG.keywords.some(k => k.keyword.toLowerCase() === kw.toLowerCase())) return;
    CONFIG.keywords.push({ keyword: kw, campaign: camp });
    kwInput.value = '';
    campInput.value = '';
    renderKeywords();
  }

  function showStatus(msg, type) {
    const el = document.getElementById('wl-status');
    el.textContent = msg;
    el.className = `active ${type}`;
  }

  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  function findChatItems() {
    const selectors = [
      'div[role="listitem"]',
      'div[data-testid="cell-frame-container"]'
    ];
    for (const sel of selectors) {
      const items = document.querySelectorAll(sel);
      if (items.length > 0) return Array.from(items);
    }
    return [];
  }

  function getPhoneNumber(chatItem) {
    const spans = chatItem.querySelectorAll('span[title]');
    for (const s of spans) {
      const t = s.getAttribute('title') || '';
      if (/^\+?\d[\d\s\-()]{7,15}$/.test(t)) return t.trim();
    }

    const label = chatItem.getAttribute('aria-label') || '';
    const m = label.match(/\+?\d[\d\s\-()]{7,15}/);
    if (m) return m[0].trim();

    return null;
  }

  function normalize(n) {
    return n.replace(/[\s\-()]/g, '');
  }

  function getMessages() {
    const selectors = [
      'div.message-in',
      'div.message-out',
      'div[data-testid="msg-container"]'
    ];
    for (const sel of selectors) {
      const msgs = document.querySelectorAll(sel);
      if (msgs.length > 0) return Array.from(msgs);
    }
    return [];
  }

  function getMessageText(msgEl) {
    const sels = ['span.selectable-text', 'span[dir="auto"]', 'span._ao3e'];
    for (const s of sels) {
      const els = msgEl.querySelectorAll(s);
      for (const el of els) {
        const t = el.textContent?.trim();
        if (t) return t;
      }
    }
    return msgEl.textContent?.trim() || '';
  }

  let scanResults = [];

  async function startScan() {
    const btn = document.getElementById('wl-btn-scan');
    const results = document.getElementById('wl-results');
    btn.disabled = true;
    btn.textContent = 'Escaneando...';
    results.className = 'active';
    results.innerHTML = '<em style="color:#8696a0">Buscando chats...</em>';
    showStatus('Iniciando escaneo...', 'info');

    await sleep(300);

    const chatItems = findChatItems();
    if (chatItems.length === 0) {
      results.innerHTML = '<em style="color:#ea4335">No se encontraron chats. Recargá la página.</em>';
      btn.disabled = false;
      btn.textContent = 'Escanear chats';
      return;
    }

    showStatus(`Encontrados ${chatItems.length} chats. Escaneando...`, 'info');

    const leads = [];
    const seen = new Set();
    const max = Math.min(chatItems.length, CONFIG.maxChats);

    for (let i = 0; i < max; i++) {
      const item = chatItems[i];
      const phone = getPhoneNumber(item);

      if (!phone) continue;
      const norm = normalize(phone);
      if (seen.has(norm)) continue;
      seen.add(norm);

      item.click();
      await sleep(CONFIG.clickDelay);

      const messages = getMessages();
      for (const msg of messages) {
        const text = getMessageText(msg).toLowerCase();
        if (!text) continue;

        for (const kw of CONFIG.keywords) {
          if (text.includes(kw.keyword.toLowerCase())) {
            const exists = leads.some(l =>
              normalize(l.number) === norm && l.campaign === kw.campaign
            );
            if (!exists) {
              leads.push({
                number: phone,
                campaign: kw.campaign,
                keyword: kw.keyword,
                date: new Date().toLocaleDateString('es-AR'),
                snippet: text.substring(0, 80)
              });
            }
            break;
          }
        }
      }
    }

    scanResults = leads;
    localStorage.setItem('whatsapp_leads', JSON.stringify(leads));

    if (leads.length === 0) {
      results.innerHTML = '<em style="color:#8696a0">No se encontraron leads con esas palabras clave.</em>';
      showStatus('Escaneo completado. Sin leads nuevos.', 'info');
    } else {
      results.innerHTML = leads.map(l => `
        <div class="wl-result-item">
          <div class="wl-result-num">${l.number}</div>
          <div class="wl-result-camp">${l.campaign} (${l.keyword})</div>
          <div class="wl-result-msg">"${l.snippet}..."</div>
        </div>
      `).join('');
      showStatus(`${leads.length} lead(s) encontrados`, 'success');
    }

    btn.disabled = false;
    btn.textContent = 'Escanear chats';
  }

  function copyToClipboard() {
    if (scanResults.length === 0) {
      showStatus('Primero escaneá los chats', 'error');
      return;
    }
    const lines = scanResults.map(l => `${l.number}\t${l.campaign}\t${l.keyword}\t${l.date}`);
    const text = lines.join('\n');
    navigator.clipboard.writeText(text).then(() => {
      showStatus(`${scanResults.length} lead(s) copiados al portapapeles. Pegá en Google Sheets.`, 'success');
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      showStatus(`${scanResults.length} lead(s) copiados`, 'success');
    });
  }

  function downloadCSV() {
    if (scanResults.length === 0) {
      showStatus('Primero escaneá los chats', 'error');
      return;
    }
    const header = 'Telefono,Campaña,Palabra Clave,Fecha,Mensaje';
    const rows = scanResults.map(l =>
      `"${l.number}","${l.campaign}","${l.keyword}","${l.date}","${l.snippet.replace(/"/g, '""')}"`
    );
    const csv = '\uFEFF' + header + '\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `whatsapp_leads_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showStatus('CSV descargado', 'success');
  }

  function downloadJSON() {
    if (scanResults.length === 0) {
      showStatus('Primero escaneá los chats', 'error');
      return;
    }
    const json = JSON.stringify(scanResults, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `whatsapp_leads_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showStatus('JSON descargado. Ejecutá: python3 leads_whatsapp.py', 'success');
  }

  createPanel();
  console.log('[WhatsApp Leads] Panel cargado. Configurá keywords y clickeá Escanear.');
})();
