// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia dei reparti e dei loro profili di accesso: la lista
//        (`amm.reparti`, `createListaStore`) e il profilo del reparto aperto
//        nel drawer (`RepartoProfiloEditor`).
// ------------------------------------------------------------
//
// ⭐ Dal 2026-09-27 la lista e' `createListaStore` (brief-db-liste-datatable-
//    grezze riga 5): prima era un elenco letto tutto in una volta, con la
//    guardia anti-race scritta a mano e nessuna pagina — la guardia ora la
//    porta il core (`useListaEmptyStateFetch`), come per ogni lista.
// ⭐ Non e' `createCrudStore`: i reparti nascono altrove (unita'
//    organizzative), qui si configura solo il loro PROFILO, che ha un
//    contratto suo (`currentProfilo` letto dal drawer, non il ritorno).
// ⚠️ Parte piena: e' un catalogo, non una ricerca. Ordine del preset
//    (`descrizione asc`).

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import {
  listReparti,
  getProfiloReparto,
  putProfiloReparto
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const { emitDataChanged } = useTabEvents()

export const useRepartiStore = createListaStore('amm-reparti', {
  fetchPage: listReparti,
  startsEmpty: false,
  orderBy: 'descrizione',
  extend: () => {
    const currentProfilo = ref(null)
    const loadingProfilo = ref(false)

    async function fetchProfilo(uoId) {
      loadingProfilo.value = true
      try {
        const res = await getProfiloReparto(uoId)
        currentProfilo.value = res.data.data
      } finally {
        loadingProfilo.value = false
      }
    }

    async function saveProfilo(uoId, aree, azioni, richiedeSecondoFattore) {
      const res = await putProfiloReparto(uoId, aree, azioni, richiedeSecondoFattore)
      currentProfilo.value = res.data.data
      emitDataChanged(TAB_ENTITIES.PROFILO_REPARTO, uoId)
      return res.data.data
    }

    return { currentProfilo, loadingProfilo, fetchProfilo, saveProfilo }
  },
})
