function actualizarCJ() {
  copiarExacto('1eVeMN1_f-RL2caN_Y9pq3DNEez3TeVTZ', 'AGENDADOS', 'CONFIRMADOS CJ');
}

function actualizarBM() {
  copiarExacto('12fWJpIBpr3GH7Yj57iyyndm_m37rr7V2', 'AGENDADOS', 'CONFIRMADOS BM');
}

function actualizarTodo() {
  const r = [];
  try { actualizarCJ(); r.push('CJ: OK'); } catch (e) { r.push('CJ: ' + e.message); }
  try { actualizarBM(); r.push('BM: OK'); } catch (e) { r.push('BM: ' + e.message); }
  SpreadsheetApp.getUi().alert(r.join('\n'));
}

function copiarExacto(sourceId, sheetName, destSheetName) {
  const src = SpreadsheetApp.openById(sourceId).getSheetByName(sheetName);
  const dstSS = SpreadsheetApp.getActiveSpreadsheet();
  const nueva = src.copyTo(dstSS);
  try { eliminarTabla(nueva.getSheetId(), dstSS.getId()); } catch(e) {}
  const vieja = dstSS.getSheetByName(destSheetName);
  if (vieja) dstSS.deleteSheet(vieja);
  nueva.setName(destSheetName);
  nueva.activate();
  const lr = nueva.getLastRow(), lc = nueva.getLastColumn();
  if (lr >= 4) {
    try {
      const flt = nueva.getFilter();
      if (flt) flt.remove();
      nueva.getRange(4, 1, lr - 3, lc).createFilter();
    } catch(e) {}
  }
}

function eliminarTabla(sheetId, spreadsheetId) {
  const token = ScriptApp.getOAuthToken();
  const getUrl = 'https://sheets.googleapis.com/v4/spreadsheets/' + spreadsheetId + '?fields=sheets(properties.sheetId,tables)';
  const resp = UrlFetchApp.fetch(getUrl, { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) return;
  const data = JSON.parse(resp);
  if (!data.sheets) return;
  const reqs = [];
  for (const s of data.sheets) {
    if (s.properties.sheetId !== sheetId) continue;
    for (const t of (s.tables || [])) {
      reqs.push({ deleteTable: { tableRange: { sheetId: sheetId, startRowIndex: t.tableRange.startRowIndex, endRowIndex: t.tableRange.endRowIndex, startColumnIndex: t.tableRange.startColumnIndex, endColumnIndex: t.tableRange.endColumnIndex } } });
    }
  }
  if (!reqs.length) return;
  UrlFetchApp.fetch('https://sheets.googleapis.com/v4/spreadsheets/' + spreadsheetId + ':batchUpdate', { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, payload: JSON.stringify({ requests: reqs }), muteHttpExceptions: true });
}

function programarAutomatizacion() {
  const t = ScriptApp.getProjectTriggers().filter(x => x.getHandlerFunction() === 'actualizarTodo');
  if (t.length) { t.forEach(x => ScriptApp.deleteTrigger(x)); }
  ScriptApp.newTrigger('actualizarTodo').timeBased().atHour(6).nearMinute(30).everyDays(1).inTimezone('America/Lima').create();
  SpreadsheetApp.getUi().alert('Programado: todos los dias a las 6:30 AM');
}

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Automatizacion')
    .addItem('Actualizar CJ', 'actualizarCJ')
    .addItem('Actualizar BM', 'actualizarBM')
    .addItem('Actualizar TODO', 'actualizarTodo')
    .addSeparator()
    .addItem('Programar 6:30 AM', 'programarAutomatizacion')
    .addToUi();
}
