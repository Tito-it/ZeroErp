// Scopo: Store Pinia admin CRUD per ui.lista_definizione (Blocco F
//        Fase 2 - DEF-5b). Espone:
//          - items, loading, hasSearched (lista completa, anche disattive)
//          - fetchAll()             — GET /admin/definizioni/
//          - getById(id)            — GET /admin/definizioni/<id>/
//          - create(payload)        — POST con Idempotency-Key
//          - update(id, payload)    — PATCH (tutti i campi mutabili)
//          - destroy(id)            — DELETE (RESTRICT FK -> 409 in uso)
//
// emitDataChanged fired post-write su `TAB_ENTITIES.UI_DEFINIZIONE` per
// auto-refresh cross-tab. La pagina tecnica e' SUPER_ADMIN-only e
// l'autorizzazione e' gestita lato BE da `IsAdminZeroERP`.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import {
  createAdminDefinizione,
  deleteAdminDefinizione,
  getAdminDefinizione,
  listAdminDefinizioniAdmin,
  updateAdminDefinizione,
} from '../../core/api/ui-admin-api'

export const useUiDefinizioneAdminStore = defineStore('ui-definizione-admin', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  // Scopo: Carica tutte le definizioni (incluse disattivate). Sostituisce
  //        gli items.
  // ⛔ `totalRecords` viene dal BACKEND (`count`), NON da `items.length`.
  //    Era `items.value.length`, cioe' un'eco: un numero derivato dalle righe
  //    non puo' dire niente SULLE righe. Serve come asserzione al guard
  //    anti-troncamento di `<ListaConfigurabile>` in modalita' `paginata:
  //    false` — se un giorno l'endpoint impaginasse, le due grandezze
  //    divergono e la lista lo dichiara invece di mostrare un sottoinsieme
  //    facendolo passare per l'insieme.
  async function fetchAll() {
    loading.value = true
    try {
      const res = await listAdminDefinizioniAdmin()
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio singolo per pre-popolare drawer in edit. Non muta
  //        items: lo store si limita a inoltrare la response.
  async function getById(listaId) {
    const res = await getAdminDefinizione(listaId)
    return res.data.data
  }

  // Scopo: Crea una nuova definizione (Idempotency-Key dall'interceptor di `core/api.js`)
  //        (UNIQUE codice mappato lato BE).
  async function create(payload) {
    const res = await createAdminDefinizione(payload)
    emitDataChanged(TAB_ENTITIES.UI_DEFINIZIONE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi mutabili.
  async function update(listaId, payload) {
    const res = await updateAdminDefinizione(listaId, payload)
    emitDataChanged(TAB_ENTITIES.UI_DEFINIZIONE, listaId)
    return res.data.data
  }

  // Scopo: Cancella definizione. In caso di FK RESTRICT (lista in uso)
  //        il BE solleva E_UI_DEFINIZIONE_IN_USO -> 409: l'errore
  //        risale al caller per mostrare il banner.
  async function destroy(listaId) {
    const res = await deleteAdminDefinizione(listaId)
    emitDataChanged(TAB_ENTITIES.UI_DEFINIZIONE, listaId)
    return res.data.data
  }

  // Scopo: Reset al logout. Pulisce items + flag stato (pattern
  //        userScoped: true).
  function clearUserState() {
    items.value = []
    totalRecords.value = 0
    loading.value = false
    hasSearched.value = false
  }

  return {
    items, totalRecords, loading, hasSearched,
    fetchAll, getById, create, update, destroy,
    clearUserState,
  }
}, { userScoped: true })
