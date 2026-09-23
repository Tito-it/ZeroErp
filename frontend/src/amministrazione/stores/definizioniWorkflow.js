// Store Pinia (sola lettura) per le edizioni di workflow versionate (Fase 2 Slice 1a).
// La lista parte piena (config admin). Le azioni fork/nuova-versione/pubblica
// arrivano in Slice 1b (lockstep con la conversione DEFINER delle fn DB).
// userScoped: contiene dati/filtri dell'utente loggato → reset al logout.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { listDefinizioniWorkflow } from '../api/definizioniWorkflow'

// ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
//    di partenza E il contratto che `FiltriLista` legge per il segno dei filtri
//    attivi. Due letterali divergerebbero al primo filtro aggiunto.
const FILTRI_DEFAULT = { tipo_prestazione_id: null, emittente_fiscale_id: null }

export const useDefinizioniWorkflowStore = defineStore('amm-definizioni-workflow', () => {
  const items = ref([])
  const loading = ref(false)
  const filters = ref({ ...FILTRI_DEFAULT })

  async function load() {
    loading.value = true
    try {
      const params = {}
      if (filters.value.tipo_prestazione_id) params.tipo_prestazione_id = filters.value.tipo_prestazione_id
      if (filters.value.emittente_fiscale_id) params.emittente_fiscale_id = filters.value.emittente_fiscale_id
      const res = await listDefinizioniWorkflow(params)
      items.value = res.data.data.results
    } finally {
      loading.value = false
    }
  }

  // Il contratto che `FiltriLista` legge. ⚠️ Questa lista non ha paginazione —
  // si legge tutta in un colpo — quindi `azzeraFiltri` non ha nessun `offset`
  // da riportare a zero, e il composable non lo inventa.
  const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
    filters, filterDefaults: FILTRI_DEFAULT, fetchList: load,
  })

  return { items, loading, filters, load, chiaviFiltro, filtriDefault, azzeraFiltri }
}, { userScoped: true })
