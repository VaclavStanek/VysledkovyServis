/**
 * Výsledkový servis – SAMOSTATNÝ Apps Script Web App pro list „Právě běží".
 *
 * Běží ve TVÉM Google účtu jako oddělený skript – do cizí tabulky se NIC nepřidává.
 * Skript jen ČTE (read-only) tabulku podle jejího ID (musíš k ní mít aspoň přístup ke
 * čtení) a vrací obsah listu jako JSON {"values": [[hlavička…],[řádek…]]}. Appka to
 * čte přes obyčejný HTTP GET (jako XML z hasicovo). Žádný API klíč / service account.
 *
 * Nasazení (na script.google.com, ne v tabulce):
 *   1) script.google.com → Nový projekt.
 *   2) Vlož tenhle kód, do SHEET_ID dej ID z URL tabulky
 *      (…/spreadsheets/d/<TADY_JE_ID>/edit).
 *   3) Ulož. Nasadit → Nové nasazení → typ „Webová aplikace".
 *      Spustit jako: Já.  Přístup: Kdokoli.  → Nasadit → povol přístup.
 *   4) Zkopíruj URL (…/exec) a vlož ji v appce (📊 Google Tabulka).
 */
var SHEET_ID = 'SEM_VLOZ_ID_TABULKY';
var SHEET_NAME = 'Právě běží';
var TOKEN = ''; // prázdné = bez tokenu; jinak appka volá URL s ?token=<hodnota>

function doGet(e) {
  if (TOKEN && (!e || !e.parameter || e.parameter.token !== TOKEN)) {
    return _json({ error: 'Neplatný token' });
  }
  var sh = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  if (!sh) return _json({ error: 'List "' + SHEET_NAME + '" nenalezen' });
  var values = sh.getDataRange().getValues().map(function (row) {
    return row.map(function (c) { return (c === null || c === undefined) ? '' : String(c); });
  });
  return _json({ values: values });
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
