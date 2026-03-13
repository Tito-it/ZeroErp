// Pinia store per la gestione reparti e profili permessi.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listReparti,
  getProfiloReparto,
  putProfiloReparto
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'

const { emitDataChanged } = useTabEvents()

export const useRepartiStore = defineStore('amm-reparti', () => {
  const items = ref([])
  const loading = ref(false)
  const currentProfilo = ref(null)
  const loadingProfilo = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res = await listReparti()
      items.value = res.data.data.results
    } finally {
      loading.value = false
    }
  }

  async function fetchProfilo(uoId) {
    loadingProfilo.value = true
    try {
      const res = await getProfiloReparto(uoId)
      currentProfilo.value = res.data.data
    } finally {
      loadingProfilo.value = false
    }
  }

  async function saveProfilo(uoId, aree, azioni) {
    const res = await putProfiloReparto(uoId, aree, azioni)
    currentProfilo.value = res.data.data
    emitDataChanged('profilo-reparto', uoId)
    return res.data.data
  }

  return {
    items,
    loading,
    currentProfilo,
    loadingProfilo,
    fetchList,
    fetchProfilo,
    saveProfilo
  }
})
