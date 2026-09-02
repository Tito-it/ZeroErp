// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista TITOLI IVA DI UN SOGGETTO
//        (`anagrafiche.soggetto_titoli_iva`, lista 62), consumata dal drawer
//        omonimo attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-02). Il drawer teneva le righe in due `ref` locali e
// chiamava l'endpoint senza parametri: la lista non paginava, non si potevano
// scegliere le colonne e non si poteva scaricare niente — cioe' era fuori dallo
// standard delle altre quaranta liste, ma senza che niente lo dicesse. Lo
// scaffolding `useDrawerTabLista` quelle tre cose le porta gia', e in cambio
// vuole il contratto di `useSearchTable`: e' questo store.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI, ed e' la distinzione che il BB
//    fa sua: `soggettoId` e' il contesto (arriva dal path dell'endpoint), i
//    filtri sono le scelte dell'operatore — e al cambio padre i secondi si
//    azzerano mentre il primo si riscrive.
//
// ⚠️ `userScoped: true`: la lista porta dati che l'operatore vede per il suo
//    perimetro emittente (la RLS filtra i titoli per emittente in whitelist).
//    Senza, al logout resterebbero in memoria (`feedback_pinia_userscoped`).
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { listSoggettoTitoliIva } from '../api/anagrafiche'

export const useSoggettoTitoliIvaStore = defineStore('anagrafiche-soggetto-titoli-iva', () => {
  // Il soggetto corrente, scritto dal drawer via `parentField` del BB.
  const soggettoId = ref(null)

  const filters = ref({
    // Dichiarata perche' fa parte del contratto di `useSearchTable`, che la
    // scrive su deep-link `?search=`. ⚠️ L'endpoint NON ha ricerca testuale e
    // `buildParams` la ignora: meglio dichiararla che farla nascere per
    // assegnazione.
    search: '',
    limit: PAGINATION.DEFAULT_ROWS,
    offset: 0,
    // ⛔ NESSUN `order_by` di partenza, ed e' voluto: senza indicazioni il
    //    backend applica l'ordinamento STORICO — validita' piu' lunga per
    //    prima, titoli senza scadenza in cima. Scrivere qui una colonna
    //    qualsiasi cambierebbe l'ordine di apertura di una lista che tutti
    //    leggono dall'alto, e lo farebbe senza che nessuno l'abbia chiesto.
    order_by: null,
    order_dir: null,
  })

  // `alwaysFetch`: non e' una lista che parte vuota in attesa di una ricerca —
  // il soggetto e' gia' scelto quando il drawer si apre.
  const {
    items, totalRecords, loading, hasSearched, fetchList: fetchListBase, svuota,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f) => {
      const params = { limit: f.limit, offset: f.offset }
      // ⚠️ `order_by` si manda solo se c'e': mandarlo vuoto significherebbe
      //    chiedere al backend un ordinamento che poi lui scarta — la cosa
      //    giusta per il motivo sbagliato.
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      return params
    },
    fetchPage: (params) => listSoggettoTitoliIva(soggettoId.value, params),
  })

  // ⛔ Senza soggetto non si chiama: l'id sta nel PATH dell'endpoint, e una
  //    fetch con `undefined` non tornerebbe una lista vuota — tornerebbe 404.
  async function fetchList() {
    if (!soggettoId.value) return
    await fetchListBase()
  }

  function reset() {
    // `svuota` del BB e non un clear a mano: invalida anche le fetch in volo,
    // cosi' la risposta del soggetto precedente non ripopola la lista.
    svuota()
    soggettoId.value = null
    filters.value.offset = 0
    // ⚠️ Anche `search`, che oggi questa lista non usa: il contratto di
    //    `useSearchTable` la scrive comunque (deep-link `?search=`), e un reset
    //    parziale e' il posto dove il primo filtro aggiunto domani sopravvive
    //    al cambio di soggetto — mostrando righe filtrate come se fossero tutte.
    filters.value.search = ''
    filters.value.order_by = null
    filters.value.order_dir = null
  }

  return {
    items, totalRecords, loading, hasSearched, filters, soggettoId,
    fetchList, reset,
  }
}, {
  userScoped: true,
})
