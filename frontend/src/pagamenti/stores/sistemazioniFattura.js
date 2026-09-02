// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista ATTI DI SISTEMAZIONE DI UNA FATTURA
//        (`pagamenti.sistemazioni_fattura`, lista 61), consumata dal drawer
//        dell'eccedenza attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-02). Il drawer teneva gli atti in tre `ref` locali
// (righe, totale, «letti») e chiamava l'endpoint senza parametri: la lista non
// paginava, non si potevano scegliere le colonne e non si poteva scaricare
// niente. La ragione scritta era «gli atti di UNA fattura sono pochi per
// modello» — che e' una previsione sui DATI, e una previsione sui dati non
// decide la forma di una lista (regola zero). Decisione di Tid: sullo standard.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI, ed e' la distinzione che il BB fa
//    sua: `fatturaId` e' il contesto (arriva dal path dell'endpoint), i filtri
//    sono le scelte dell'operatore — e al cambio padre i secondi si azzerano
//    mentre il primo si riscrive.
//
// ⛔ `erroreCaricamento` e' uno stato NOSTRO, e non e' difensivismo: il drawer
//    distingue TRE casi — atti presenti · nessun atto · non letti — e il terzo
//    non si spaccia per il secondo. «Su questo documento non ha ancora deciso
//    nessuno» e' un'affermazione su cui qualcuno decide di nuovo; «non sono
//    riuscito a leggerli» e' il contrario, e il BB della lista non ha modo di
//    dirlo (`hasSearched` resta falso in entrambi i casi).
//
// ⚠️ `userScoped: true`: gli atti stanno dietro la RLS del perimetro emittente
//    dell'operatore. Senza, al logout resterebbero in memoria
//    (`feedback_pinia_userscoped`).
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { listSistemazioniFattura } from '../api/pagamenti'

export const useSistemazioniFatturaStore = defineStore('pagamenti-sistemazioni-fattura', () => {
  // La fattura corrente, scritta dal drawer via `parentField` del BB.
  const fatturaId = ref(null)
  // Terzo caso: l'ultima lettura e' fallita. Si riscrive a OGNI fetch, nei due
  // versi — un flag che si accende e non si spegne piu' lascerebbe l'avviso
  // sopra una lista che nel frattempo si e' caricata.
  const erroreCaricamento = ref(false)

  const filters = ref({
    // Dichiarata perche' fa parte del contratto di `useSearchTable`, che la
    // scrive su deep-link `?search=`. ⚠️ L'endpoint NON ha ricerca testuale e
    // `buildParams` la ignora: meglio dichiararla che farla nascere per
    // assegnazione.
    search: '',
    limit: PAGINATION.DEFAULT_ROWS,
    offset: 0,
    // ⛔ NESSUN `order_by` di partenza, ed e' voluto: senza indicazioni il
    //    backend ordina per `s.id`, cioe' nell'ordine in cui gli atti sono
    //    stati decisi — che e' come si legge un registro. Scrivere qui una
    //    colonna qualsiasi cambierebbe l'ordine di apertura senza che nessuno
    //    l'abbia chiesto.
    order_by: null,
    order_dir: null,
  })

  // `alwaysFetch`: non e' una lista che parte vuota in attesa di una ricerca —
  // la fattura e' gia' scelta quando il drawer si apre.
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
    fetchPage: (params) => listSistemazioniFattura(fatturaId.value, params),
  })

  // ⛔ Senza fattura non si chiama: l'id sta nel PATH dell'endpoint, e una fetch
  //    con `undefined` non tornerebbe una lista vuota — tornerebbe 404.
  // ⚠️ L'esito si legge dal ritorno di `fetchListBase`, che e' `false` anche
  //    quando la risposta viene SCARTATA perche' stantia. Li' non c'e' nessun
  //    errore da dichiarare: una fetch piu' recente e' in volo e sara' lei a
  //    scrivere lo stato. Per questo l'errore si accende solo su `catch`.
  async function fetchList(opzioni) {
    if (!fatturaId.value) return false
    try {
      const esito = await fetchListBase(opzioni)
      erroreCaricamento.value = false
      return esito
    } catch (e) {
      erroreCaricamento.value = true
      throw e
    }
  }

  function reset() {
    // `svuota` del BB e non un clear a mano: invalida anche le fetch in volo,
    // cosi' la risposta della fattura precedente non ripopola la lista.
    svuota()
    fatturaId.value = null
    erroreCaricamento.value = false
    filters.value.offset = 0
    // ⚠️ Anche `search`, che oggi questa lista non usa: il contratto di
    //    `useSearchTable` la scrive comunque (deep-link `?search=`), e un reset
    //    parziale e' il posto dove il primo filtro aggiunto domani sopravvive
    //    al cambio di fattura — mostrando righe filtrate come se fossero tutte.
    filters.value.search = ''
    filters.value.order_by = null
    filters.value.order_dir = null
  }

  return {
    items, totalRecords, loading, hasSearched, filters, fatturaId,
    erroreCaricamento,
    fetchList, reset,
  }
}, {
  userScoped: true,
})
