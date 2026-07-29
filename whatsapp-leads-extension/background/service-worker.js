const SHEETS_API_BASE = 'https://sheets.googleapis.com/v4/spreadsheets';

function extractSpreadsheetId(url) {
  const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

function getAuthToken(interactive = false) {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else if (!token) {
        reject(new Error('No se obtuvo token de autenticación'));
      } else {
        resolve(token);
      }
    });
  });
}

async function appendToSheet(leads, spreadsheetUrl, sheetName, columnStart) {
  const spreadsheetId = extractSpreadsheetId(spreadsheetUrl);
  if (!spreadsheetId) {
    throw new Error('URL de hoja de cálculo inválida');
  }

  const token = await getAuthToken(true);

  const columnIndex = columnStart.charCodeAt(0) - 65;
  const secondCol = String.fromCharCode(65 + columnIndex + 1);
  const thirdCol = String.fromCharCode(65 + columnIndex + 2);
  const fourthCol = String.fromCharCode(65 + columnIndex + 3);

  const range = `'${sheetName}'!${columnStart}:${fourthCol}`;

  const rows = leads.map(lead => [
    lead.number,
    lead.campaign,
    lead.keyword,
    new Date(lead.date).toLocaleString('es-AR')
  ]);

  const response = await fetch(
    `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}:append?valueInputOption=USER_ENTERED`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        values: rows
      })
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `Error HTTP ${response.status}`);
  }

  return await response.json();
}

async function getExistingNumbers(spreadsheetUrl, sheetName, columnStart) {
  const spreadsheetId = extractSpreadsheetId(spreadsheetUrl);
  if (!spreadsheetId) return [];

  try {
    const token = await getAuthToken(true);
    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/'${sheetName}'!${columnStart}:${columnStart}?majorDimension=COLUMNS`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    if (!response.ok) return [];
    const data = await response.json();
    return (data.values?.[0] || []).map(v => v.replace(/[\s\-\(\)]/g, ''));
  } catch {
    return [];
  }
}

async function ensureHeaderRow(spreadsheetUrl, sheetName, columnStart) {
  const spreadsheetId = extractSpreadsheetId(spreadsheetUrl);
  if (!spreadsheetId) return;

  try {
    const token = await getAuthToken(true);
    const col2 = String.fromCharCode(columnStart.charCodeAt(0) + 1);
    const col3 = String.fromCharCode(columnStart.charCodeAt(0) + 2);
    const col4 = String.fromCharCode(columnStart.charCodeAt(0) + 3);

    const checkResp = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/'${sheetName}'!${columnStart}1:${col4}1?majorDimension=ROWS`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    if (checkResp.ok) {
      const checkData = await checkResp.json();
      if (checkData.values?.[0]?.[0]) return;
    }

    await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/'${sheetName}'!${columnStart}1:${col4}1?valueInputOption=USER_ENTERED`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          values: [['Teléfono', 'Campaña', 'Palabra Clave', 'Fecha']]
        })
      }
    );
  } catch {
  }
}

function filterNewLeads(leads, existingNumbers) {
  const existingSet = new Set(existingNumbers);
  return leads.filter(lead => !existingSet.has(lead.numberNormalized));
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'authGoogle') {
    getAuthToken(true)
      .then(token => sendResponse({ success: true, token }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === 'exportToSheets') {
    chrome.storage.sync.get(['spreadsheetUrl', 'sheetName', 'columnStart'], async (config) => {
      try {
        if (!config.spreadsheetUrl) {
          throw new Error('URL de hoja no configurada');
        }

        const spreadsheetUrl = config.spreadsheetUrl;
        const sheetName = config.sheetName || 'Hoja1';
        const columnStart = config.columnStart || 'A';

        await ensureHeaderRow(spreadsheetUrl, sheetName, columnStart);

        const existingNumbers = await getExistingNumbers(spreadsheetUrl, sheetName, columnStart);
        const newLeads = filterNewLeads(request.leads || [], existingNumbers);

        if (newLeads.length === 0) {
          sendResponse({ success: true, message: 'No hay leads nuevos para exportar' });
          return;
        }

        await appendToSheet(newLeads, spreadsheetUrl, sheetName, columnStart);
        sendResponse({ success: true, exported: newLeads.length });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    });
    return true;
  }
});
