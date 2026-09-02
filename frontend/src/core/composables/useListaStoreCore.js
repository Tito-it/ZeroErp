// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: lo SCHELETRO di uno store-lista — i filtri nella forma che
//        `useSearchTable` si aspetta, la fetch paginata, il cancello
//        empty-state, la sospensione e il reset. Tutto cio' che serve a una
//        lista, e niente di cio' che serve al CRUD.
//
// Estratto il 2026-09-02 (regola del 2, ok Tid) da `createCrudStore` — che ne
// era l'unico proprietario — nel momento in cui sono nati TRE store-lista
// scritti a mano (`sistemazioniFattura`, `soggettoTitoliIva`,
// `titoliIvaSfondati`). Non potevano usare la factory: due di loro hanno il
// padre nel PATH dell'endpoint (`list(parentId, params)`), forma che
// `createCrudStore` non conosce — e nessuno dei tre e' un CRUD.
//
// ⛔ E LE TRE COPIE AVEVANO GIA' LO STESSO IDENTICO DIFETTO, che e' il modo in
//    cui una duplicazione si fa notare: nessuna esponeva `fetchSospesa`.
//    `useListaConfigurabilePage.onConfigLoaded` la scrive con un guard
//    `'fetchSospesa' in store`, quindi uno store che non la dichiara **non
//    rompe niente** — semplicemente non si sospende mai. Col cancello di
//    perimetro emittente alzato la lista continuava a chiedere pagine che il
//    backend rifiuta con 422, a ogni click, mentre a video c'era il pannello
//    «scegli un emittente». Tre copie, un difetto, zero errori.
//
// ⭐ E' UN COMPOSABLE, NON UNO STORE, e nemmeno un oggetto condiviso: ogni
//    chiamata costruisce il proprio stato. Esportare un'istanza per
//    de-duplicare sembrerebbe funzionare col primo consumatore e romperebbe il
//    secondo in silenzio (`feedback_estrarre_non_condividere_stato`).
//    Lo consumano `createCrudStore` (che ci aggiunge il CRUD) e
//    `createListaStore` (che lo impacchetta e basta).
import { ref } from 'vue'
import { useListaEmptyStateFetch } from './useListaEmptyStateFetch'
import { PAGINATION } from '../constants'

// Params:
//   - fetchPage: (params) => Promise<response axios>. Con `parentField`, la
//       firma diventa (parentId, params) — e' l'endpoint annidato.
//   - parentField: nome della proprieta' che porta l'id del PADRE (`soggettoId`,
//       `fatturaId`). ⚠️ E' contesto, non un filtro: al cambio padre i filtri si
//       azzerano, questa si riscrive.
//   - filterDefaults: filtri di dominio con il loro default (no
//       search/limit/offset/order_*, che ci sono sempre).
//   - gateKeys: sottoinsieme di filterDefaults che conta come «ricerca attiva»
//       per il cancello empty-state. Irrilevante con startsEmpty:false.
//   - startsEmpty: true → la lista parte vuota in attesa di una ricerca;
//       false → parte piena (always-fetch).
//   - orderBy / orderDir: ordinamento di partenza.
export function useListaStoreCore({
  fetchPage,
  parentField = null,
  filterDefaults = {},
  gateKeys = [],
  startsEmpty = true,
  orderBy = null,
  orderDir = 'asc',
} = {}) {
  // L'id del padre, quando la lista ne ha uno. `null` = nessun padre scelto.
  const parentId = ref(null)

  // ⛔ IL TERZO CASO. Una lista vuota e una lista NON LETTA si assomigliano —
  //    `items` e' `[]` in entrambi i casi, e `hasSearched` resta falso — ma
  //    dicono cose opposte: «qui non c'e' niente» e' un'affermazione su cui
  //    qualcuno decide, «non sono riuscito a leggere» dice solo che non si sa.
  //    Sta nel BB e non nel singolo store perche' la distinzione non e' di
  //    dominio: vale per ogni lista, e finora nessuna delle tre poteva farla.
  const erroreCaricamento = ref(false)

  const filters = ref({
    // ⚠️ `search` c'e' SEMPRE, anche sulle liste che non cercano: fa parte del
    //    contratto di `useSearchTable`, che la scrive sul deep-link `?search=`.
    //    Dichiararla e' meglio che farla nascere per assegnazione.
    search: '',
    ...filterDefaults,
    limit: PAGINATION.DEFAULT_ROWS,
    offset: 0,
    order_by: orderBy,
    order_dir: orderDir,
  })

  const {
    items, totalRecords, loading, hasSearched, sospesa: fetchSospesa,
    fetchList: fetchListBase, svuota,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: !startsEmpty,
    hasActiveFilters: (f) => gateKeys.some((k) => f[k] != null),
    buildParams: (f, searchTerm) => {
      const params = {}
      if (searchTerm.length >= 3) params.search = searchTerm
      // Ogni filtro di dominio valorizzato, anche quelli non-gate (es.
      // `attivo: true`: default valorizzato, inviato sempre).
      for (const k of Object.keys(filterDefaults)) {
        if (f[k] != null) params[k] = f[k]
      }
      params.limit = f.limit
      params.offset = f.offset
      // ⚠️ L'ordinamento si manda solo se c'e': mandarlo vuoto significherebbe
      //    chiedere al backend un ordinamento che poi lui scarta — la cosa
      //    giusta per il motivo sbagliato.
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      return params
    },
    fetchPage: (params) => (
      parentField ? fetchPage(parentId.value, params) : fetchPage(params)
    ),
  })

  // ⛔ Senza padre non si chiama: l'id sta nel PATH dell'endpoint, e una fetch
  //    con `undefined` non tornerebbe una lista vuota — tornerebbe 404.
  // ⚠️ L'esito di `fetchListBase` e' `false` anche quando la risposta viene
  //    SCARTATA perche' stantia, e li' NON c'e' nessun errore da dichiarare:
  //    una fetch piu' recente e' in volo e sara' lei a scrivere lo stato. Per
  //    questo l'errore si accende solo su `catch`.
  // ⛔ E il rifiuto NON si ri-solleva: qui e' gia' gestito — diventa
  //    `erroreCaricamento`, che il caller rende come avviso. Ri-sollevarlo dopo
  //    averlo trattato lo farebbe atterrare in un `Promise.all` senza `catch`
  //    (`useDrawerTabLista`), cioe' una unhandled rejection che non dice a
  //    nessuno niente in piu' di quello che l'avviso dice gia'.
  async function fetchList(opzioni) {
    if (parentField && !parentId.value) return false
    try {
      const esito = await fetchListBase(opzioni)
      erroreCaricamento.value = false
      return esito
    } catch {
      erroreCaricamento.value = true
      return false
    }
  }

  // Scopo: riporta la lista allo stato di partenza — usata dai BB di drawer
  //        quando il padre sparisce (`useDrawerTabLista`).
  // ⚠️ `svuota` del BB e non un clear a mano: invalida anche le fetch in volo,
  //    cosi' la risposta del padre precedente non ripopola la lista.
  // ⚠️ E si azzerano TUTTI i filtri, non solo l'offset: un reset parziale e' il
  //    posto dove il primo filtro aggiunto domani sopravvive al cambio di
  //    padre, mostrando righe filtrate come se fossero tutte.
  function reset() {
    svuota()
    parentId.value = null
    erroreCaricamento.value = false
    filters.value = {
      search: '',
      ...filterDefaults,
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      order_by: orderBy,
      order_dir: orderDir,
    }
  }

  const esposto = {
    items, totalRecords, loading, hasSearched, filters,
    // Alzata da chi conosce il motivo (oggi solo il cancello di perimetro
    // emittente, in `useListaConfigurabilePage`): finche' e' true la lista non
    // interroga il backend. Si scrive nei DUE versi, mai una volta sola.
    fetchSospesa,
    erroreCaricamento,
    fetchList, svuota, reset,
  }
  // ⭐ Il padre si espone COL SUO NOME (`soggettoId`, `fatturaId`), non come
  //    `parentId`: e' il nome che il caller scrive in `parentField` di
  //    `useDrawerTabLista`, ed e' quello che si legge nei componenti.
  if (parentField) esposto[parentField] = parentId
  return esposto
}
