// Costanti di dominio per gli ordini di vendita. Stati interni allineati a
// `config.stati_doc_ordini.codice_interno` (seed). Stessi valori usati dal BE
// come literal in `apps/vendite/services/ordini_service.py`. Mantenere
// allineato: il BE matcha il `stato_codice_interno` ritornato dalla vista,
// niente normalizzazione.

export const STATO_ORDINE = Object.freeze({
  DRAFT: 'DRAFT',
  CONFERMATO: 'CONFERMATO',
  ALLOCATO: 'ALLOCATO',
  SPEDITO: 'SPEDITO',
  CONSEGNATO: 'CONSEGNATO',
  ANNULLATO: 'ANNULLATO',
  FATTURATO: 'FATTURATO',
})

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
// Decisione §12.4(a) analisi-ordini-vendita.md: stampa DISACCOPPIATA dallo
// stato → `EntityPdfButton` usa SEMPRE l'anteprima on-demand (ristampabile,
// nessun archivio persistito in v1). Per questo passiamo tutti gli stati
// consultabili come `stati-preview` e una lista vuota come `stati-con-documento`
// (la modalita' "scarica dall'archivio" si attivera' quando esistera' un trigger
// di generazione/persistenza, es. agganciato alla conferma — Decisione §12.4(b)).
export const STATI_ORDINE_ANTEPRIMA_PDF = Object.freeze([
  STATO_ORDINE.DRAFT,
  STATO_ORDINE.CONFERMATO,
  STATO_ORDINE.ALLOCATO,
  STATO_ORDINE.SPEDITO,
  STATO_ORDINE.CONSEGNATO,
  STATO_ORDINE.FATTURATO,
])

export const STATI_ORDINE_CON_DOCUMENTO = Object.freeze([])
