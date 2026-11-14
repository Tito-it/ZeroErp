// Costanti di dominio per le offerte commerciali. Stati interni allineati
// a `config.stati_doc_offerte.codice_interno` (seed step 1 brief DB,
// migration `20260524-02`). Stessi valori usati dal BE come literal in
// `apps/vendite/services/offerte_service.py::StatoOfferta`. Mantenere
// allineato bit-per-bit: il BE matcha il `stato_codice_interno` ritornato
// dalla view, niente normalizzazione.
//
// **Cosa NON sta qui dopo il refactor data-driven 2026-05-26**: la lista
// degli stati editabili era duplicata col BE (`_STATI_EDITABILI` lato
// service); ora `can_edit_testata` arriva da `script.fn_available_actions_offerta`
// e il FE non ricalcola piu' nulla. Cosi' anche per la matrice delle
// azioni per stato (era in `OffertaDrawer.drawerActions` hardcoded).
//
// ⛔ Dal 2026-11-13 (brief-db-stati-documento-dal-vocabolario §6.7-§6.8) non
// stanno qui nemmeno «quali stati sono terminali» (la capability
// `stato_terminale`, dalla colonna `terminale` del vocabolario) ne' «in quali
// stati la scadenza conta» (`is_scaduta` della vista dice gia' la regola
// intera: validita' passata e nessun esito del cliente). Erano
// `STATI_OFFERTA_TERMINALI` e `STATI_OFFERTA_SEGNALA_SCADENZA`, ritirate.

export const STATO_OFFERTA = Object.freeze({
  BOZZA: 'BOZZA',
  EMESSA: 'EMESSA',
  ACCETTATA: 'ACCETTATA',
  RIFIUTATA: 'RIFIUTATA',
  ANNULLATA: 'ANNULLATA',
  SUPERATA: 'SUPERATA',
})

// Mappa stato→modalita'-PDF (anteprima bozza / archivio post-emissione /
// append allegati) ora DATA-DRIVEN via capability `pdf` di
// `fn_available_actions_offerta` (`config.stati_doc_offerte.pdf_mode` +
// `pdf_allow_allegati`), consumata da `EntityPdfButton`.

// Le colonne della testata che il form dell'offerta (inline in
// `OffertaDrawer`) MOSTRA, per `useTestataDocumento`
// (brief-db-testata-dopo-emissione, R-FE-3). ⚠️ Deve dire gli stessi campi del
// form (`testata.bloccato('…')`): lo presidia `campiFormTestata.spec.js`. I dati
// della fornitura (utenza) non ci sono: li governa `can_edit_utility`.
export const CAMPI_FORM_TESTATA_OFFERTA = Object.freeze([
  'emittente_fiscale_id',
  // Il cliente si cambia in bozza (2026-10-13); la utility lo segue e si spegne
  // con lui (`utility_id` non e' piu' un campo a se').
  'billing_account_id',
  'listino_id',
  'tipo_variazione_globale',
  'valore_variazione_globale',
  'valuta_id',
  'validita_dal',
  'validita_al',
  // Come si addebitano i canoni (F-2, F-7): fermi fuori bozza come le
  // condizioni (`E_DOC_CONDIZIONI_FUORI_BOZZA`).
  'generazione_canone',
  'mese_partenza_canone',
])
