// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista di PRESIDIO dei titoli IVA sfondati
//        (`anagrafiche.titoli_iva_sfondati`, lista 63).
//
// PERCHE' ESISTE. La view teneva le righe in uno `ref` locale e chiamava
// l'endpoint senza parametri. Il passaggio a `<ListaConfigurabile>` vuole il
// contratto atteso da `useSearchTable`/`useListaConfigurabilePage` — `filters`
// con limit/offset/order_by/order_dir/search, `hasSearched`, `fetchList`,
// `items`, `totalRecords`, `loading` — e senza store andrebbero riscritti a
// mano onPage/onSort/pageActions, cioe' duplicato il building block.
//
// ⭐ E la lista PAGINA, dal 2026-09-02. Prima l'endpoint restituiva i primi 500
//    e non lo diceva a nessuno: su un presidio — che esiste perche' una
//    forzatura di plafond non sfugga — dal 501-esimo caso in poi il difetto non
//    si vedeva. Decisione di Tid: paginarla sullo standard.
//
// userScoped: reset al logout (`feedback_pinia_userscoped`).
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { listTitoliIvaSfondati } from '../api/anagrafiche'

export const useTitoliIvaSfondatiStore = defineStore('anagrafiche-titoli-iva-sfondati', () => {
  const filters = ref({
    // Dichiarata perche' fa parte del contratto di `useSearchTable`, che la
    // scrive su deep-link `?search=`. ⚠️ L'endpoint NON ha ricerca testuale e
    // `buildParams` la ignora: meglio dichiararla che farla nascere per
    // assegnazione.
    search: '',
    limit: PAGINATION.DEFAULT_ROWS,
    offset: 0,
    // ⛔ Default allineato al BE: la piu' GRAVE per prima. Su un presidio
    //    l'ordine non e' una preferenza — e' cio' che mette in cima la cosa da
    //    guardare per prima.
    order_by: 'eccedenza',
    order_dir: 'desc',
  })

  // `alwaysFetch`: non e' una lista che parte vuota in attesa di una ricerca.
  // Un presidio vuoto perche' nessuno ha ancora cercato non presidia niente.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f) => ({
      limit: f.limit,
      offset: f.offset,
      order_by: f.order_by,
      order_dir: f.order_dir,
    }),
    fetchPage: listTitoliIvaSfondati,
  })

  return { items, totalRecords, loading, hasSearched, filters, fetchList }
}, {
  userScoped: true,
})
