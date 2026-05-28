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

// Stati terminali (workflow morto). Usato dal banner del drawer per
// scegliere severity `warn` (terminale) vs `info` (post-BOZZA non
// terminale, EMESSA/ACCETTATA). Il BE espone `can_edit_testata=false`
// per entrambi i casi: la distinzione UI vive solo qui.
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

// Stati con documento PDF gia' generato (post-emissione): il PDF e'
// cristallizzato, si scarica dalla lista archiviata. Usato da
// `EntityPdfButton` come `stati-con-documento`. EMESSA incluso: il BE
// genera il PDF alla transizione BOZZA->EMESSA.
export const STATI_OFFERTA_CON_DOCUMENTO = Object.freeze([
  STATO_OFFERTA.EMESSA,
  STATO_OFFERTA.ACCETTATA,
  STATO_OFFERTA.RIFIUTATA,
  STATO_OFFERTA.SUPERATA,
  STATO_OFFERTA.ANNULLATA,
])

// Stati in cui e' consentito l'append di allegati al documento gia'
// generato (regola dominio: "fino a EMESSA compresa", da ACCETTATA in
// poi il documento e' chiuso). Usato da `EntityPdfButton` come
// `stati-append-allegati`.
export const STATI_OFFERTA_APPEND_ALLEGATI = Object.freeze([
  STATO_OFFERTA.EMESSA,
])

// Stati in cui mostrare l'azione "Anteprima PDF" (preview on-the-fly,
// no persist). Usato da `EntityPdfButton` come `stati-preview`.
export const STATI_OFFERTA_ANTEPRIMA_PDF = Object.freeze([
  STATO_OFFERTA.BOZZA,
])
