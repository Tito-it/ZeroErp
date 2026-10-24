// Scopo: API client per il namespace /api/v1/ui/* — personalizzazioni
//        liste (config, catalogo, preferenza) e dashboard configurabili
//        (config, contatori KPI, preferenza).
//
// Convenzione: ritornano la response Axios; lo unwrap dell'envelope
// `{data, meta}` viene fatto a livello composable (`useApiHandler` o
// `useListaConfig`).

import api from '../api'

const BASE = '/ui'

// Scopo: Risolve la configurazione effettiva di una lista per l'utente.
// Restituisce {colonne, ordinamento, filtri, pagina_dimensione, colonne_nuove}.
//
// ⭐ `emittenteEsplicito` dice al backend che la lista si sta aprendo con un
//    emittente GIA' fissato (il tab dentro il drawer di un emittente). Senza,
//    l'envelope tornerebbe `richiede_scelta_emittente: true` su una lista non
//    certificata multi-emittente, e il pannello chiederebbe di scegliere
//    l'emittente che l'operatore ha gia' aperto davanti.
// ⚠️ Il NOME sul filo (`emittente_esplicito`, che il backend tiene in
//    `perimetro_emittente.PARAM_EMITTENTE_ESPLICITO`) vive solo qui: chi chiama
//    passa un valore, non un parametro di query. E «assente» si decide in un
//    posto solo — null, undefined o stringa vuota non sono una scelta, e
//    mandarli varrebbe come non mandare niente.
export function getListaConfig(codice, { emittenteEsplicito = null } = {}) {
  const params = {}
  if (emittenteEsplicito !== null && emittenteEsplicito !== undefined && emittenteEsplicito !== '') {
    params.emittente_esplicito = emittenteEsplicito
  }
  return api.get(`${BASE}/liste/${encodeURIComponent(codice)}/config/`, { params })
}

// Scopo: Le misure «righe per pagina» di TUTTI i paginatori e i due default,
// dal catalogo DB `ui.misure_pagina`: {misure, default_compatta,
// default_pagina}. La legge solo il BB `core/misurePagina.js`, una volta per
// sessione.
export function getMisurePagina() {
  return api.get(`${BASE}/misure-pagina/`)
}

// Scopo: Catalogo colonne per la modale di personalizzazione.
// Restituisce {colonne: [...]} arricchito di metadati (etichetta, gruppo,
// formato, ecc.). Filtrato per i permessi dell'utente: colonne BLOCCATE
// non compaiono.
export function getListaCatalogo(codice) {
  return api.get(`${BASE}/liste/${encodeURIComponent(codice)}/catalogo/`)
}

// Scopo: UPSERT preferenza utente. Idempotency-Key obbligatoria (modalita'
// forte di `handle_post_json` lato BE): la mette l'interceptor di `core/api.js`.
export function putListaPreferenza(codice, configurazione) {
  return api.put(
    `${BASE}/liste/${encodeURIComponent(codice)}/preferenza/`,
    configurazione,
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
// l'`Idempotency-Key` la mette l'interceptor di `core/api.js` (§A5, 2026-10-20).
export function ignorePresetUpdate(codice) {
  return api.post(
    `${BASE}/liste/${encodeURIComponent(codice)}/preferenza/ignore-preset-update/`,
    null,
  )
}

// ── Dashboard configurabili (card KPI home) ──────────────────────────

// Scopo: Risolve la configurazione effettiva di una dashboard per
// l'utente. Restituisce {widget[], dimensione_max, widget_nuovi,
// preset_aggiornato}. Ogni widget porta codice/ordine/visibile piu' i
// campi freschi del catalogo (etichetta, etichetta_i18n_key,
// tipo_widget, deep_link, contatore_key, soglia). Gia' filtrato per i
// permessi dell'utente lato fn DB: il FE non filtra.
export function getDashboardConfig(codice) {
  return api.get(`${BASE}/dashboard/${encodeURIComponent(codice)}/config/`)
}

// Scopo: Contatori KPI dei widget visibili, in un solo giro.
// Restituisce {contatori: {<contatore_key>: {valore, ok}}}.
// Nessuna chiave passata dal client di proposito: il BE calcola solo le
// key dei widget che la fn DB ha concesso a questo utente (altrimenti
// sarebbe una lettura cross-area). `ok:false` = contatore degradato,
// la singola card mostra lo stato non disponibile.
export function getDashboardContatori(codice) {
  return api.get(`${BASE}/dashboard/${encodeURIComponent(codice)}/contatori/`)
}

// Scopo: UPSERT preferenza dashboard. Idempotency-Key obbligatoria.
// Payload: {widget: [{codice, ordine, visibile}], dimensione_max}.
export function putDashboardPreferenza(codice, configurazione) {
  return api.put(
    `${BASE}/dashboard/${encodeURIComponent(codice)}/preferenza/`,
    configurazione,
  )
}

// Scopo: Elimina preferenza dashboard (torna al default di ruolo).
export function deleteDashboardPreferenza(codice) {
  return api.delete(`${BASE}/dashboard/${encodeURIComponent(codice)}/preferenza/`)
}

// Scopo: Tombstone "ignora banner preset aggiornato" per la dashboard.
export function ignoreDashboardPresetUpdate(codice) {
  return api.post(
    `${BASE}/dashboard/${encodeURIComponent(codice)}/preferenza/ignore-preset-update/`,
    null,
  )
}
