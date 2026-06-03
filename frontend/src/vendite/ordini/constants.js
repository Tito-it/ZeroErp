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
