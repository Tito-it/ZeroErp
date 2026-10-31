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
// Quello che resta qui e' solo **logica UI di presentation** che il BE
// volutamente non conosce: discriminare "terminale" da "intermedio
// editabile fuori BOZZA" per la severity del banner, e quali stati hanno
// senso col badge "SCADUTA".

export const STATO_OFFERTA = Object.freeze({
  BOZZA: 'BOZZA',
  EMESSA: 'EMESSA',
  ACCETTATA: 'ACCETTATA',
  RIFIUTATA: 'RIFIUTATA',
  ANNULLATA: 'ANNULLATA',
  SUPERATA: 'SUPERATA',
})

// Stati in cui l'operatore non ha piu' nulla da fare. Usato dal banner del
// drawer per scegliere severity `warn` vs `info` (post-BOZZA non terminale,
// EMESSA/ACCETTATA). Il BE espone `can_edit_testata=false` per entrambi i casi:
// la distinzione UI vive solo qui.
//
// ⚠️ `SUPERATA` resta in elenco, ma dal 2026-08-28 NON e' piu' «workflow morto»:
//    il database la riporta a `EMESSA` da se' quando l'ultima revisione viva
//    viene annullata e il padre torna a essere l'offerta del lineage. La
//    transizione e' `manuale: false` — nessuna azione, nessun pulsante — quindi
//    per chi guarda non cambia niente e la severity resta quella giusta.
//    ⛔ Cambia il PERCHE', non il comportamento: chiamarlo «morto» avrebbe
//    portato il prossimo lettore a costruirci sopra un'inferenza sbagliata.
export const STATI_OFFERTA_TERMINALI = Object.freeze([
  STATO_OFFERTA.RIFIUTATA,
  STATO_OFFERTA.ANNULLATA,
  STATO_OFFERTA.SUPERATA,
])

// Stati su cui ha senso il badge "SCADUTA" (validita_al < today). Negli
// stati terminali la scadenza non e' un fatto operativo da segnalare
// (l'offerta non e' piu' viva).
export const STATI_OFFERTA_SEGNALA_SCADENZA = Object.freeze([
  STATO_OFFERTA.BOZZA,
  STATO_OFFERTA.EMESSA,
])

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
