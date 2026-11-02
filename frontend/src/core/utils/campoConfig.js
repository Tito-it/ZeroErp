// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La risoluzione di UN campo del drawer generico delle tabelle config
//        (`GenericConfigDrawer`) a partire dal metadata che il BE legge dal
//        catalogo: quale WIDGET lo rende e quale CHIAVE i18n lo etichetta.
//        Pura e senza import proprio per essere provata da sola: un ramo
//        sbagliato qui non fallisce — mostra una casella di testo dove serviva
//        una tendina, o un id grezzo dove serviva un nome.
// Note: ⭐ Il drawer resta metadata-driven (nessuna riga per tabella): il
//       widget discende dal MODELLO — una FK verso una tabella ammessa al
//       lookup generico e' una `LookupSelect` (col `valueField` =
//       `references_column`: una FK non punta per forza a `id`), una FK verso
//       una tabella che il lookup non serve resta un valore a mano — numero o
//       testo secondo il tipo — E LO DICHIARA (hint), una `date` e' un
//       `DatePicker`. Chi decide se la FK e' montabile come lookup e' il BE
//       (`references_lookup`: tabella in whitelist E colonna referenziata fra
//       quelle che il lookup porta), che possiede entrambe le cose.
//       ⚠️ Le chiavi delle etichette sono COSTRUITE (`config_panel.campi.<col>`):
//       `check_i18n_keys` non le vede. Il presidio e' il test sul DB provvisto
//       `apps/core/tests/db/test_config_panel_registro_db.py`, che attraversa
//       ogni colonna di ogni tabella del registro e pretende la chiave nei
//       locales veri; a video il ripiego e' il nome della colonna
//       (`labelOrCode`), mai la chiave.
// ------------------------------------------------------------

export const WIDGET = Object.freeze({
  TEXT: 'text',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  JSON: 'json',
  DATE: 'date',
  LOOKUP: 'lookup',
  // Una FK verso una tabella che il lookup generico NON serve: valore a mano
  // (numero o testo secondo `type`), con l'hint che nomina tabella e colonna
  // — «id grezzo» dichiarato, non nascosto.
  FK_ID: 'fk_id',
})

export const PREFISSO_CAMPI = 'config_panel.campi'
export const PREFISSO_TABELLE = 'config_panel.tabelle'

// Scopo: la chiave i18n dell'etichetta di una colonna del pannello.
export function chiaveEtichettaCampo(col) {
  return `${PREFISSO_CAMPI}.${col.name}`
}

// Scopo: la chiave i18n dell'etichetta di una TABELLA del registro: la rel
//        stessa (`schema.tabella`) sotto il prefisso — il punto e' gia' il
//        separatore di vue-i18n, quindi `config_panel.tabelle.config.ambiti`.
export function chiaveEtichettaTabella(rel) {
  return `${PREFISSO_TABELLE}.${rel}`
}

// Scopo: il widget che rende la colonna, dal metadata BE
//        (`type`, `references`, `references_lookup`).
export function widgetPerColonna(col) {
  if (col.references) return col.references_lookup ? WIDGET.LOOKUP : WIDGET.FK_ID
  switch (col.type) {
    case 'boolean': return WIDGET.BOOLEAN
    case 'number': return WIDGET.NUMBER
    case 'json': return WIDGET.JSON
    case 'date': return WIDGET.DATE
    default: return WIDGET.TEXT
  }
}
