/**
 * Výsledkový servis – Apps Script Web App pro list „Právě běží".
 *
 * Vrací obsah listu jako JSON {"values": [[hlavička…], [řádek…], …]}, který appka
 * čte přes obyčejný HTTP GET (jako XML z hasicovo). Tabulka zůstává SOUKROMÁ –
 * skript běží pod tvým účtem a ven pouští jen tahle data, ne přístup k dokumentu.
 * Není potřeba žádný API klíč ani service account.
 *
 * Nasazení:
 *   1) V tabulce: Rozšíření → Apps Script.
 *   2) Vlož tenhle kód, ulož.
 *   3) Nasadit → Nové nasazení → typ „Webová aplikace".
 *   4) Spustit jako: Já.  Přístup: Kdokoli.
 *   5) Nasadit → zkopíruj URL (…/exec) a vlož ji v appce (📊 Google Tabulka).
 *
 * Když list přejmenuješ, uprav SHEET_NAME. Volitelně token: nastav TOKEN a v appce
 * přidej na konec URL „?token=…".
 */
var SHEET_NAME = 'Právě běží';
var TOKEN = ''; // prázdné = bez tokenu; jinak appka musí volat URL s ?token=<hodnota>

function doGet(e) {
  if (TOKEN && (!e || !e.parameter || e.parameter.token !== TOKEN)) {
    return _json({ error: 'Neplatný token' });
  }
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sh) return _json({ error: 'List "' + SHEET_NAME + '" nenalezen' });
  var values = sh.getDataRange().getValues().map(function (row) {
    return row.map(function (c) { return (c === null || c === undefined) ? '' : String(c); });
  });
  return _json({ values: values });
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
