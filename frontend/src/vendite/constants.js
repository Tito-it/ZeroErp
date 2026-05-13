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
// EVASO e' lo stato terminale post-push commessa: transizione automatica
// ACCETTATO -> EVASO scatenata dal BE (preventivi_service.push_a_commessa)
// quando tutte le righe pushable sono in commessa.
export const STATO_PREVENTIVO = Object.freeze({
  DRAFT: 'DRAFT',
  EMESSO: 'EMESSO',
  ACCETTATO: 'ACCETTATO',
  EVASO: 'EVASO',
  RIFIUTATO: 'RIFIUTATO',
  SCADUTO: 'SCADUTO',
  ANNULLATO: 'ANNULLATO',
})

// Chiave nel meta della pratica APPROVAZIONE_PREZZO che linka la riga
// preventivo target. Coerente col BE
// `_approvazioni_prezzo_constants.META_KEY_RIGA_PREVENTIVO_ID`.
export const META_KEY_RIGA_PREVENTIVO_ID = 'riga_preventivo_id'

// Codici origine prezzo del pricing resolver v5 (6 valori, modello unificato
// componenti BoM 2026-05-13). Allineato al CHECK DB su
// `vendite.preventivi_righe_componenti.origine_prezzo` e su
// `vendite.preventivi_righe.origine_prezzo` (quando esteso).
// `LISTINO_BUNDLE`: nuovo STADIO 0 del resolver bundle-aware — prezzo
// componente in contesto padre composito, vince su CATEGORIA standalone.
export const ORIGINE_PREZZO = Object.freeze({
  PROMO: 'PROMO',
  CONTRATTO_OVERRIDE: 'CONTRATTO_OVERRIDE',
  CONTRATTO_LISTINO: 'CONTRATTO_LISTINO',
  CATEGORIA: 'CATEGORIA',
  LISTINO_BUNDLE: 'LISTINO_BUNDLE',
  MANUALE: 'MANUALE',
})
