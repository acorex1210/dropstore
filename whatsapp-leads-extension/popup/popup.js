document.addEventListener('DOMContentLoaded', async () => {
  const spreadsheetUrl = document.getElementById('spreadsheet-url');
  const sheetName = document.getElementById('sheet-name');
  const columnStart = document.getElementById('column-start');
  const btnSaveConfig = document.getElementById('btn-save-config');
  const newKeyword = document.getElementById('new-keyword');
  const newCampaign = document.getElementById('new-campaign');
  const btnAddKeyword = document.getElementById('btn-add-keyword');
  const keywordsList = document.getElementById('keywords-list');
  const btnScan = document.getElementById('btn-scan');
  const btnAuth = document.getElementById('btn-auth');
  const status = document.getElementById('status');

  async function loadConfig() {
    const data = await chrome.storage.sync.get(['spreadsheetUrl', 'sheetName', 'columnStart', 'keywords']);
    if (data.spreadsheetUrl) spreadsheetUrl.value = data.spreadsheetUrl;
    if (data.sheetName) sheetName.value = data.sheetName;
    if (data.columnStart) columnStart.value = data.columnStart;
    renderKeywords(data.keywords || []);
  }

  function renderKeywords(keywords) {
    keywordsList.innerHTML = '';
    keywords.forEach((kw, index) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div>
          <span class="keyword-text">${kw.keyword}</span>
          <span class="campaign-text"> → ${kw.campaign}</span>
        </div>
        <button class="btn-delete" data-index="${index}">✕</button>
      `;
      keywordsList.appendChild(li);
    });

    keywordsList.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const idx = parseInt(e.target.dataset.index);
        const data = await chrome.storage.sync.get(['keywords']);
        const keywords = data.keywords || [];
        keywords.splice(idx, 1);
        await chrome.storage.sync.set({ keywords });
        renderKeywords(keywords);
      });
    });
  }

  function showStatus(message, type) {
    status.textContent = message;
    status.className = `status-bar ${type}`;
    status.classList.remove('hidden');
    setTimeout(() => status.classList.add('hidden'), 4000);
  }

  btnSaveConfig.addEventListener('click', async () => {
    const url = spreadsheetUrl.value.trim();
    if (!url) {
      showStatus('Ingresá la URL de la hoja de cálculo', 'error');
      return;
    }
    await chrome.storage.sync.set({
      spreadsheetUrl: url,
      sheetName: sheetName.value.trim() || 'Hoja1',
      columnStart: columnStart.value
    });
    showStatus('Configuración guardada', 'success');
  });

  btnAddKeyword.addEventListener('click', async () => {
    const kw = newKeyword.value.trim();
    const camp = newCampaign.value.trim();
    if (!kw || !camp) {
      showStatus('Completá palabra clave y campaña', 'error');
      return;
    }
    const data = await chrome.storage.sync.get(['keywords']);
    const keywords = data.keywords || [];
    if (keywords.some(k => k.keyword.toLowerCase() === kw.toLowerCase())) {
      showStatus('Esa palabra clave ya existe', 'error');
      return;
    }
    keywords.push({ keyword: kw, campaign: camp });
    await chrome.storage.sync.set({ keywords });
    renderKeywords(keywords);
    newKeyword.value = '';
    newCampaign.value = '';
    showStatus('Palabra clave agregada', 'success');
  });

  btnAuth.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'authGoogle' }, (response) => {
      if (response?.success) {
        showStatus('Autenticación exitosa', 'success');
      } else {
        showStatus('Error de autenticación: ' + (response?.error || 'Desconocido'), 'error');
      }
    });
  });

  btnScan.addEventListener('click', async () => {
    const data = await chrome.storage.sync.get(['spreadsheetUrl', 'keywords']);
    if (!data.spreadsheetUrl) {
      showStatus('Primero configurá la URL de la hoja', 'error');
      return;
    }
    if (!data.keywords || data.keywords.length === 0) {
      showStatus('Agregá al menos una palabra clave', 'error');
      return;
    }

    btnScan.disabled = true;
    btnScan.textContent = 'Escaneando...';

    chrome.tabs.query({}, (allTabs) => {
      const waTab = allTabs.find(t => t.url?.includes('web.whatsapp.com'));
      if (!waTab) {
        showStatus('Abrí WhatsApp Web primero', 'error');
        btnScan.disabled = false;
        btnScan.innerHTML = '<span class="btn-icon">🔍</span> Escanear WhatsApp';
        return;
      }
      chrome.tabs.sendMessage(waTab.id, { action: 'scanChats' }, (response) => {
        btnScan.disabled = false;
        btnScan.innerHTML = '<span class="btn-icon">🔍</span> Escanear WhatsApp';
        if (chrome.runtime.lastError) {
          showStatus('Error de conexión. Recargá WhatsApp Web.', 'error');
          return;
        }
        if (response?.success) {
          const count = response.leads?.length || 0;
          showStatus(`${count} lead(s) detectado(s). Exportando...`, 'info');
          chrome.runtime.sendMessage({
            action: 'exportToSheets',
            leads: response.leads
          }, (res) => {
            if (res?.success) {
              showStatus(`${count} lead(s) exportado(s) correctamente`, 'success');
            } else {
              showStatus('Error al exportar: ' + (res?.error || 'Desconocido'), 'error');
            }
          });
        } else {
          showStatus(response?.error || 'No se detectaron leads', 'info');
        }
      });
    });
  });

  loadConfig();
});
