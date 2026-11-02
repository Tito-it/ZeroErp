// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della lista «altre sessioni attive» dell'operatore
//        collegato (`core.sessioni_attive`, pannello della home): il core di
//        lista (`useListaStoreCore`) piu' il totale delle sessioni ATTIVE.
// ------------------------------------------------------------
//
// ⭐ Parte piena (`startsEmpty: false`) e si legge dal piu' recente, come il
//    preset della lista (`data_ultimo_evento desc`).
// ⭐ `totaleAttive` NON e' `totalRecords`: il secondo conta le righe TROVATE
//    dalla ricerca, il primo le sessioni che esistono (`totale_attive` del
//    backend). Il pannello si mostra, il badge conta e «revoca tutte»
//    conferma sul primo: una ricerca che non trova niente non deve far
//    sparire il pannello, ne' far dire al dialog «revocherai 1 sessione»
//    mentre ne revoca tre.
// ⚠️ `defineStore` + `useListaStoreCore` e non `createListaStore`: il totale lo
//    scrive `onPayload`, che deve chiudere su un ref nato PRIMA del core — la
//    forma di `vendite/stores/giornale`.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaStoreCore } from '../composables/useListaStoreCore'
import { listSessioni } from '../api/sessioni'

export const useSessioniAttiveStore = defineStore(
  'core-sessioni-attive',
  () => {
    const totaleAttive = ref(0)

    const base = useListaStoreCore({
      fetchPage: listSessioni,
      startsEmpty: false,
      orderBy: 'data_ultimo_evento',
      orderDir: 'desc',
      orderDirDefault: 'desc',
      onPayload: (payload) => { totaleAttive.value = payload.totale_attive ?? 0 },
    })

    function reset() {
      base.reset()
      totaleAttive.value = 0
    }

    return { ...base, reset, totaleAttive }
  },
  { userScoped: true },
)
