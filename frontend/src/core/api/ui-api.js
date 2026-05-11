// Scopo: API client per il namespace /api/v1/ui/* (personalizzazioni
//        liste). Wrappa i 4 endpoint di Blocco C: config, catalogo,
//        upsert preferenza, delete preferenza.
//
// Convenzione: ritornano la response Axios; lo unwrap dell'envelope
// `{data, meta}` viene fatto a livello composable (`useApiHandler` o
// `useListaConfig`).

import api from '../api'

const BASE = '/ui'

// Scopo: Risolve la configurazione effettiva di una lista per l'utente.
// Restituisce {colonne, ordinamento, filtri, pagina_dimensione, colonne_nuove}.
export function getListaConfig(codice) {
  return api.get(`${BASE}/liste/${encodeURIComponent(codice)}/config/`)
}

// Scopo: Catalogo colonne per la modale di personalizzazione.
// Restituisce {colonne: [...]} arricchito di metadati (etichetta, gruppo,
// formato, ecc.). Filtrato per i permessi dell'utente: colonne BLOCCATE
// non compaiono.
export function getListaCatalogo(codice) {
  return api.get(`${BASE}/liste/${encodeURIComponent(codice)}/catalogo/`)
}

// Scopo: UPSERT preferenza utente. Idempotency-Key obbligatoria — il
// composable la genera lato client per request.
export function putListaPreferenza(codice, configurazione, idempotencyKey) {
  return api.put(
    `${BASE}/liste/${encodeURIComponent(codice)}/preferenza/`,
    configurazione,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
}

// Scopo: Elimina preferenza utente per la lista. Idempotente.
export function deleteListaPreferenza(codice) {
  return api.delete(`${BASE}/liste/${encodeURIComponent(codice)}/preferenza/`)
}

// Scopo: DEF-2 — tombstone "ignora banner preset aggiornato". POST senza
// body: setta `preset_aggiornato_ignored_at = NOW()` sulla preferenza
// utente. Il flag `preset_aggiornato` di fn_resolve_lista_config torna
// FALSE finche' il preset non viene modificato di nuovo. 404 se l'utente
// non ha ancora una preferenza salvata (caso patologico).
//
// Idempotency-Key obbligatoria (handle_post_json strong mode lato BE):
// il composable la genera per request via `generateIdempotencyKey`.
export function ignorePresetUpdate(codice, idempotencyKey) {
  return api.post(
    `${BASE}/liste/${encodeURIComponent(codice)}/preferenza/ignore-preset-update/`,
    null,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
}
