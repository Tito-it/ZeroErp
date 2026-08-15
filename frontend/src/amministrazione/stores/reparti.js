// Pinia store per la gestione reparti e profili permessi.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import {
  listReparti,
  getProfiloReparto,
  putProfiloReparto
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const { emitDataChanged } = useTabEvents()

export const useRepartiStore = defineStore('amm-reparti', () => {
  const fv = useFetchVersion()
  const items = ref([])
  const loading = ref(false)
  const currentProfilo = ref(null)
  const loadingProfilo = ref(false)

  // ⚠️ Guardia anti-race (2026-08-10). Non passa dal BB `useListaEmptyStateFetch`:
  // non e' una lista filtrata/paginata ma un elenco di lookup, senza `count` da
  // leggere nell'envelope. La guardia serve lo stesso, perche' due chiamanti
  // possono ricaricare a distanza ravvicinata.
  async function fetchList() {
    const tag = fv.tag()
    loading.value = true
    try {
      const res = await listReparti()
      if (!fv.isCurrent(tag)) return
      items.value = res.data.data.results
    } finally {
      if (fv.isCurrent(tag)) loading.value = false
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
    emitDataChanged(TAB_ENTITIES.PROFILO_REPARTO, uoId)
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
}, { userScoped: true })
