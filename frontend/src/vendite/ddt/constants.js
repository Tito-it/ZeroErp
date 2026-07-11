// Costanti di dominio per i DDT di vendita. Stati interni allineati a
// `config.stati_doc_ddt.codice_interno` (seed). Stessi valori usati dal BE come
// literal in `apps/vendite/services/ddt_service.py`. Mantenere allineato: il BE
// matcha lo `stato_codice_interno` ritornato dalla vista, niente normalizzazione.
// Macchina a stati: DRAFT -> EMESSO -> SPEDITO -> CONSEGNATO (-> RESO) + ANNULLATO.
// Il `numero` e' NULL in DRAFT, assegnato dal trigger DB alla transizione EMESSO.

export const STATO_DDT = Object.freeze({
  DRAFT: 'DRAFT',
  EMESSO: 'EMESSO',
  SPEDITO: 'SPEDITO',
  CONSEGNATO: 'CONSEGNATO',
  RESO: 'RESO',
  ANNULLATO: 'ANNULLATO',
})

// Stampa DDT accompagnatorio (motore `documenti`, sorgente DDT_VENDITA).
// Flusso allineato alla famiglia vendite (mirror ordini): in DRAFT solo
// anteprima on-demand; il documento definitivo si genera all'EMISSIONE
// (DRAFT→EMESSO via /emetti/ multipart, DdtEmissioneDialog) e dagli stati
// post-bozza `EntityPdfButton`/lista aprono la gestione documentale (PDF gia'
// archiviati). ANNULLATO escluso: niente gestione documenti su un DDT annullato.
// ⚠️ TRANSITORIO: mappa stato→modalita' PDF HARDCODED lato FE (come nei domini
// gemelli). Un nuovo stato in `config.stati_doc_ddt` non riflesso qui degrada
// il bottone a disabled. Fix data-driven pianificato: capability `pdf.mode` da
// `fn_available_actions_ddt` — brief `brief-db-pdf-capabilities-data-driven.md`;
// a valle queste costanti si eliminano.
export const STATI_DDT_ANTEPRIMA_PDF = Object.freeze([
  STATO_DDT.DRAFT,
])

export const STATI_DDT_CON_DOCUMENTO = Object.freeze([
  STATO_DDT.EMESSO,
  STATO_DDT.SPEDITO,
  STATO_DDT.CONSEGNATO,
  STATO_DDT.RESO,
])
