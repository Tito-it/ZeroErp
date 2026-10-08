// Client API per i lookup statici di dominio vendite (Fase 2 refactor frontend).
// Endpoint dedicati: GET /api/v1/vendite/lookup/<nome>/
//   - tipi-variazione-contratto  -> [{codice, descrizione, ordering}]
//   - tipi-variazione-promo      -> idem (include PREZZO_FISSO)
//   - ambiti-contratto           -> [{codice: COMMODITY|COMMERCIO, ...}]
//   - modalita-pricing-contratto -> [{codice: A|B|C, ...}]
//
// Le funzioni sono pensate per essere passate a `useGlobalLookup(key, fetchFn)`
// con chiavi stabili (vedi i wrapper in `vendite/components/`).

import api from '../../core/api'

const BASE = '/vendite/lookup'

export function lookupTipiVariazioneContratto() {
  return api.get(`${BASE}/tipi-variazione-contratto/`)
}

export function lookupTipiVariazionePromo() {
  return api.get(`${BASE}/tipi-variazione-promo/`)
}

export function lookupAmbitiContratto() {
  return api.get(`${BASE}/ambiti-contratto/`)
}

// I listini che un contratto o un'offerta di questa utility e di questo
// emittente puo' scegliere: la lettura del DB (`vendite.fn_listini_selezionabili`),
// lo stesso predicato del guard del documento, quindi la tendina non propone cio'
// che il salvataggio rifiuterebbe (F-2 di brief-db-offerta-emissione-ed-erogazione).
// Sui valori del FORM: in creazione il documento non esiste. Envelope dei lookup
// `{"results": [{id, codice, descrizione}]}`. Consumer: `ListinoDocumentoSelect`.
export function lookupListiniSelezionabili(utilityId, emittenteFiscaleId) {
  return api.get(`${BASE}/listini-selezionabili/`, {
    params: { utility_id: utilityId, emittente_fiscale_id: emittenteFiscaleId },
  })
}

// Refactor modalita 2026-05-15: il lookup `modalita-pricing-contratto` (A/B/C)
// e' stato rimosso. Nel modello unificato la "modalita" non e' piu' una scelta
// utente ma una forma derivata dai dati. Nessun client la chiama piu'.
