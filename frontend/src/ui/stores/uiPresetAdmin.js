// Scopo: Store Pinia admin CRUD per ui.lista_preset (Blocco F Fase 1).
//        Espone:
//          - items, loading, hasSearched (lista preset di una lista)
//          - fetchByLista(listaId)            — lista preset
//          - listColonne(presetId)            — composizione preset
//          - listCatalogo(listaId)            — catalogo colonne grezzo
//          - create(listaId, payload)         — POST con Idempotency-Key
//          - update(presetId, payload)        — PATCH testata
//          - destroy(presetId)                — DELETE
//          - replaceColonne(presetId, body)   — PUT atomico composizione
//
// emitDataChanged fired post-write su `TAB_ENTITIES.UI_PRESET` per
// auto-refresh cross-tab (anche se in Fase 1 abbiamo una sola pagina,
// l'invariant resta utile e zero costo).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import {
  createAdminPreset,
  deleteAdminPreset,
  listAdminListaColonne,
  listAdminPresetByLista,
  listAdminPresetColonne,
  replaceAdminPresetColonne,
  updateAdminPreset,
} from '../../core/api/ui-admin-api'

export const useUiPresetAdminStore = defineStore('ui-preset-admin', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)
  const lastListaId = ref(null)

  // Scopo: Carica preset di una lista. Sostituisce gli items.
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
      const res = await listAdminPresetByLista(listaId)
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

  // Scopo: Restituisce la composizione del preset (lazy on demand).
  async function listColonne(presetId) {
    const res = await listAdminPresetColonne(presetId)
    return res.data.data
  }

  // Scopo: Restituisce il catalogo colonne grezzo della lista (per
  //        scegliere quali colonne includere nella composizione preset).
  async function listCatalogo(listaId) {
    const res = await listAdminListaColonne(listaId)
    return res.data.data
  }

  // Scopo: Crea un preset (testata). lista_id viene dal path.
  async function create(listaId, payload) {
    const res = await createAdminPreset(listaId, payload)
    emitDataChanged(TAB_ENTITIES.UI_PRESET, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi mutabili di un preset.
  async function update(presetId, payload) {
    const res = await updateAdminPreset(presetId, payload)
    emitDataChanged(TAB_ENTITIES.UI_PRESET, presetId)
    return res.data.data
  }

  // Scopo: Cancella un preset.
  async function destroy(presetId) {
    const res = await deleteAdminPreset(presetId)
    emitDataChanged(TAB_ENTITIES.UI_PRESET, presetId)
    return res.data.data
  }

  // Scopo: Replace atomico della composizione del preset.
  async function replaceColonne(presetId, payload) {
    const res = await replaceAdminPresetColonne(presetId, payload)
    emitDataChanged(TAB_ENTITIES.UI_PRESET, presetId)
    return res.data.data
  }

  // Scopo: Reset al logout. Pulisce items + last selection.
  function clearUserState() {
    items.value = []
    totalRecords.value = 0
    loading.value = false
    hasSearched.value = false
    lastListaId.value = null
  }

  return {
    items, totalRecords, loading, hasSearched, lastListaId,
    fetchByLista, listColonne, listCatalogo,
    create, update, destroy, replaceColonne,
    clearUserState,
  }
}, { userScoped: true })
