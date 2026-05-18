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

// Refactor 2026-05-18 §4.4: lookup dinamico dei listini selezionabili come
// riferimento contrattuale. Filtra `vendite.listini` per esistenza di una
// versione ATTIVA (cf. backend ListiniRepository.list_lookup_selezionabili_contratti).
// Payload `{id, codice, descrizione}` compatibile col pattern lookup generico
// — sostituisce `LookupSelect rel='vendite.listini'` nel ContrattoDrawer.
export function lookupListiniSelezionabiliContratto() {
  return api.get(`${BASE}/listini-selezionabili-contratto/`)
}

// Refactor modalita 2026-05-15: il lookup `modalita-pricing-contratto` (A/B/C)
// e' stato rimosso. Nel modello unificato la "modalita" non e' piu' una scelta
// utente ma una forma derivata dai dati. Nessun client la chiama piu'.
