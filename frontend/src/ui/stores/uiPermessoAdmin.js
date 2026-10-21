// Scopo: Store Pinia admin per ui.lista_colonna_permesso (Blocco F Fase 1).
//        UPSERT su (colonna_id, profilo_accesso_id) + DELETE per id +
//        list filtrato per lista_id (con display fields BE).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import {
  deleteAdminPermesso,
  listAdminPermessiByLista,
  upsertAdminPermesso,
} from '../../core/api/ui-admin-api'

export const useUiPermessoAdminStore = defineStore('ui-permesso-admin', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)
  const lastListaId = ref(null)

  // Scopo: Carica permessi colonna per la lista corrente.
  async function fetchByLista(listaId) {
    if (listaId == null) {
      items.value = []
      totalRecords.value = 0
      hasSearched.value = false
      lastListaId.value = null
      return
    }
    loading.value = true
    try {
      const res = await listAdminPermessiByLista(listaId)
      // ⛔ `totalRecords` dal BACKEND (`count`), NON da `items.length`: un
      // numero derivato dalle righe non puo' dire niente SULLE righe. Serve
      // come asserzione al guard anti-troncamento di `<ListaConfigurabile>`
      // in modalita' `paginata: false`.
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
      lastListaId.value = listaId
    } finally {
      loading.value = false
    }
  }

  // Scopo: UPSERT permesso. La response include id (nuovo o aggiornato).
  async function upsert(payload) {
    const res = await upsertAdminPermesso(payload)
    emitDataChanged(TAB_ENTITIES.UI_PERMESSO, res.data.data.id)
    return res.data.data
  }

  // Scopo: Cancella permesso per id (torna al default deny-list/allow-list).
  async function destroy(permessoId) {
    const res = await deleteAdminPermesso(permessoId)
    emitDataChanged(TAB_ENTITIES.UI_PERMESSO, permessoId)
    return res.data.data
  }

  function clearUserState() {
    items.value = []
    totalRecords.value = 0
    loading.value = false
    hasSearched.value = false
    lastListaId.value = null
  }

  return {
    items, totalRecords, loading, hasSearched, lastListaId,
    fetchByLista, upsert, destroy,
    clearUserState,
  }
}, { userScoped: true })
