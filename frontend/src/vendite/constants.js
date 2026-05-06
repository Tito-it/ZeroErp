// Costanti dominio vendite condivise FE.
// Mantenere allineate con `apps/vendite/services/_approvazioni_prezzo_constants.py`
// (BE) e con i seed DB (`config.stati_doc_preventivi`,
// `config.azioni_processo`).

// Stati di workflow approvazione prezzo applicabili al campo
// `vendite.preventivi_righe.stato_approvazione_prezzo` (ENUM nativo
// `config.stato_approvazione_prezzo`).
export const STATO_APPROVAZIONE = Object.freeze({
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
})

// Codici azione di processo (`config.azioni_processo.permission_codename`).
// Usati con `auth.isActionAllowed(...)` per gating UI lato FE.
export const PRICING_ACTIONS = Object.freeze({
  OVERRIDE: 'prezzo_override_manuale',
  APPROVE: 'approva_prezzo_override',
})

// Codici stato preventivo (`config.stati_doc_preventivi.codice_interno`).
// NB: 'Bozza' e' la descrizione it-IT, il codice tecnico stabile e' DRAFT.
export const STATO_PREVENTIVO = Object.freeze({
  DRAFT: 'DRAFT',
  EMESSO: 'EMESSO',
  ACCETTATO: 'ACCETTATO',
  RIFIUTATO: 'RIFIUTATO',
  SCADUTO: 'SCADUTO',
  ANNULLATO: 'ANNULLATO',
})

// Chiave nel meta della pratica APPROVAZIONE_PREZZO che linka la riga
// preventivo target. Coerente col BE
// `_approvazioni_prezzo_constants.META_KEY_RIGA_PREVENTIVO_ID`.
export const META_KEY_RIGA_PREVENTIVO_ID = 'riga_preventivo_id'
