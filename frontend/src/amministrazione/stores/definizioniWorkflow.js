// Store Pinia (sola lettura) per le edizioni di workflow versionate (Fase 2 Slice 1a).
// La lista parte piena (config admin). Le azioni fork/nuova-versione/pubblica
// arrivano in Slice 1b (lockstep con la conversione DEFINER delle fn DB).
// userScoped: contiene dati/filtri dell'utente loggato → reset al logout.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDefinizioniWorkflow } from '../api/definizioniWorkflow'

export const useDefinizioniWorkflowStore = defineStore('amm-definizioni-workflow', () => {
  const items = ref([])
  const loading = ref(false)
  const filters = ref({ tipo_prestazione_id: null, emittente_fiscale_id: null })

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

  return { items, loading, filters, load }
}, { userScoped: true })
