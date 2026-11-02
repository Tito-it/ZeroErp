// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//
// ⭐ NON E' PIU' SCRITTO A MANO (2026-09-02, regola del 2 · ok Tid): il corpo
//    vive in `createListaStore` / `useListaStoreCore`. Era la terza di TRE
//    copie, e come le altre due non esponeva `fetchSospesa` — quindi col
//    cancello di perimetro emittente alzato continuava a chiedere pagine che il
//    backend rifiuta con 422. Il BB la espone per tutte.
import { createListaStore } from '../../core/stores/createListaStore'
import { listTitoliIvaSfondati } from '../api/anagrafiche'

export const useTitoliIvaSfondatiStore = createListaStore(
  'anagrafiche-titoli-iva-sfondati',
  {
    fetchPage: listTitoliIvaSfondati,
    // ⛔ Un presidio vuoto perche' nessuno ha ancora cercato non presidia
    //    niente: parte piena.
    startsEmpty: false,
    // ⛔ Default allineato al BE: la piu' GRAVE per prima. Su un presidio
    //    l'ordine non e' una preferenza — e' cio' che mette in cima la cosa da
    //    guardare per prima.
    orderBy: 'eccedenza',
    orderDir: 'desc',
  },
)
