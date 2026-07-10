// Costanti di dominio per gli ordini di vendita. Stati interni allineati a
// `config.stati_doc_ordini.codice_interno` (seed). Stessi valori usati dal BE
// come literal in `apps/vendite/services/ordini_service.py`. Mantenere
// allineato: il BE matcha il `stato_codice_interno` ritornato dalla vista,
// niente normalizzazione.

export const STATO_ORDINE = Object.freeze({
  DRAFT: 'DRAFT',
  CONFERMATO: 'CONFERMATO',
  // Ordine parzialmente evaso: almeno un DDT generato ma con residuo aperto
  // (config.stati_doc_ordini id 9, fase IN_CORSO, non terminale). Aggiunto con
  // la slice evasione DDT: l'ordine resta evadibile finche' resta residuo.
  PARZIALMENTE_EVASO: 'PARZIALMENTE_EVASO',
  EVASO: 'EVASO',
  ALLOCATO: 'ALLOCATO',
  SPEDITO: 'SPEDITO',
  CONSEGNATO: 'CONSEGNATO',
  ANNULLATO: 'ANNULLATO',
  FATTURATO: 'FATTURATO',
})

// Stati dell'ordine dai quali e' possibile generare un DDT di evasione: c'e'
// residuo da evadere (CONFERMATO = tutto aperto, PARZIALMENTE_EVASO = residuo
// parziale). Guida il montaggio dell'OrdineEvasionePanel nel drawer ordine.
export const STATI_ORDINE_EVADIBILI = Object.freeze([
  STATO_ORDINE.CONFERMATO,
  STATO_ORDINE.PARZIALMENTE_EVASO,
])

// Trigger di fatturazione (asse OdV-specifico): governa *quando* l'ordine pusha
// a commessa. Ereditato da `billing_account.fatturazione_ordini`, sovrascrivibile
// in testata. Valori allineati al CHECK DB su vendite.ordini.fatturazione_trigger.
export const FATTURAZIONE_TRIGGER = Object.freeze({
  CONFERMATO: 'CONFERMATO',
  SPEDITO: 'SPEDITO',
  CONSEGNATO: 'CONSEGNATO',
})

export const FATTURAZIONE_TRIGGER_CODES = Object.freeze([
  FATTURAZIONE_TRIGGER.CONFERMATO,
  FATTURAZIONE_TRIGGER.SPEDITO,
  FATTURAZIONE_TRIGGER.CONSEGNATO,
])

// Stampa conferma d'ordine (motore `documenti`, sorgente ORDINE_VENDITA).
// Flusso allineato alla famiglia vendite (§6 brief-ordini-stampa.md, rettifica
// 2026-06-05): in DRAFT solo anteprima on-demand; il documento definitivo si
// genera alla CONFERMA (DRAFT→CONFERMATO via /emetti/, OrdineEmissioneDialog) e
// dagli stati post-bozza `EntityPdfButton`/lista aprono la gestione documentale
// (PDF gia' archiviati). ANNULLATO escluso: niente gestione documenti su un
// ordine annullato. Detta gli stati il modello `config.stati_doc_ordini`
// (data-driven), non valori hardcodati a casaccio (feedback_no_hardcoded_ids).
export const STATI_ORDINE_ANTEPRIMA_PDF = Object.freeze([
  STATO_ORDINE.DRAFT,
])

export const STATI_ORDINE_CON_DOCUMENTO = Object.freeze([
  STATO_ORDINE.CONFERMATO,
  STATO_ORDINE.EVASO,
  STATO_ORDINE.ALLOCATO,
  STATO_ORDINE.SPEDITO,
  STATO_ORDINE.CONSEGNATO,
  STATO_ORDINE.FATTURATO,
])
