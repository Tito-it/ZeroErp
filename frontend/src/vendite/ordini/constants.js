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
// parziale). Guida la disponibilita' dell'azione «Genera DDT» (OrdineEvasioneDialog).
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

// Stampa conferma d'ordine (motore `documenti`, sorgente ORDINE_VENDITA):
// in DRAFT solo anteprima on-demand; il documento definitivo si genera alla
// CONFERMA (DRAFT→CONFERMATO via /emetti/, OrdineEmissioneDialog).
//
// La mappa stato→modalita'-PDF e' interamente DATA-DRIVEN via `pdf_mode`
// (`config.stati_doc_ordini.pdf_mode`): il DRAWER la legge dalla capability
// `pdf` di `fn_available_actions_ordine` (`EntityPdfButton`); la LISTA la legge
// dalla colonna `pdf_mode` di `vendite.vw_ordini_lista` (`OrdiniSearchTable`,
// `row.pdf_mode === PDF_MODE.ARCHIVE`). Nessuna lista di stati hardcoded qui.
