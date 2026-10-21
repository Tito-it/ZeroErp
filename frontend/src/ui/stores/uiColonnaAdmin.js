// Scopo: Store Pinia admin CRUD per ui.lista_colonna (Blocco F Fase 2
//        - DEF-5b). Espone:
//          - items, loading, hasSearched (catalogo della lista corrente)
//          - lastListaId
//          - fetchByLista(listaId)    — GET /admin/definizioni/<id>/colonne/
//          - getById(id)              — GET /admin/colonne/<id>/
//          - create(listaId, payload) — POST con Idempotency-Key
//          - update(id, payload)      — PATCH (lista_id immutabile)
//          - destroy(id)              — DELETE (soft-block preferenze)
//
// emitDataChanged fired post-write su `TAB_ENTITIES.UI_COLONNA`. La
// pagina tecnica e' SUPER_ADMIN-only (BE: `IsAdminZeroERP`).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import {
  createAdminColonna,
  deleteAdminColonna,
  getAdminColonna,
  listAdminColonneAdmin,
  updateAdminColonna,
} from '../../core/api/ui-admin-api'

export const useUiColonnaAdminStore = defineStore('ui-colonna-admin', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)
  const lastListaId = ref(null)

  // Scopo: Carica le colonne admin (incluse disattivate, campi completi)
  //        della lista indicata. Sostituisce gli items.
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
      const res = await listAdminColonneAdmin(listaId)
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

  // Scopo: Dettaglio singolo per pre-popolare drawer in edit. Non muta
  //        items.
  async function getById(colonnaId) {
    const res = await getAdminColonna(colonnaId)
    return res.data.data
  }

  // Scopo: Crea una nuova colonna nella lista indicata.
  async function create(listaId, payload) {
    const res = await createAdminColonna(listaId, payload)
    emitDataChanged(TAB_ENTITIES.UI_COLONNA, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi mutabili.
  async function update(colonnaId, payload) {
    const res = await updateAdminColonna(colonnaId, payload)
    emitDataChanged(TAB_ENTITIES.UI_COLONNA, colonnaId)
    return res.data.data
  }

  // Scopo: Cancella colonna. Soft-block applicativo se referenziata da
  //        preferenze utente -> 409 con E_UI_COLONNA_IN_USO; l'errore
  //        risale al caller.
  async function destroy(colonnaId) {
    const res = await deleteAdminColonna(colonnaId)
    emitDataChanged(TAB_ENTITIES.UI_COLONNA, colonnaId)
    return res.data.data
  }

  // Scopo: Reset al logout (pattern userScoped: true).
  function clearUserState() {
    items.value = []
    totalRecords.value = 0
    loading.value = false
    hasSearched.value = false
    lastListaId.value = null
  }

  return {
    items, totalRecords, loading, hasSearched, lastListaId,
    fetchByLista, getById, create, update, destroy,
    clearUserState,
  }
}, { userScoped: true })
