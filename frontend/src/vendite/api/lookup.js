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

export function lookupModalitaPricingContratto() {
  return api.get(`${BASE}/modalita-pricing-contratto/`)
}
