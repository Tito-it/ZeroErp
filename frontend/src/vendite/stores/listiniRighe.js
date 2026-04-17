// Store Pinia per la gestione righe prezzo di una versione listino.
// Gestisce paginazione server-side, filtri (search articolo, billing_account)
// e reload post-operazione (create/delete riga, variazione %).
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listRighe } from '../api/listini'

export const useListiniRigheStore = defineStore('vendite-listini-righe', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  // Contesto corrente: listino e versione. Impostati dal drawer padre.
  const listinoId = ref(null)
  const versioneId = ref(null)

  const filters = ref({
    search: '',
    billing_account_id: null,
    // Default 10 righe/pagina coerente col pattern master-detail inline
    // (frontend-standards: 10 righe + rows-per-page-options [10, 25]).
    limit: 10,
    offset: 0,
    order_by: 'articolo_descrizione',
    order_dir: 'asc'
  })

  // Scopo: Imposta il contesto listino/versione e resetta filtri e dati.
  function setContext(newListinoId, newVersioneId) {
    listinoId.value = newListinoId
    versioneId.value = newVersioneId
    items.value = []
    totalRecords.value = 0
    filters.value.search = ''
    filters.value.billing_account_id = null
    filters.value.offset = 0
  }

  // Scopo: Svuota dati e contesto alla chiusura del drawer.
  function clearContext() {
    listinoId.value = null
    versioneId.value = null
    items.value = []
    totalRecords.value = 0
  }

  // Scopo: Carica la pagina corrente di righe dal backend con filtri attivi.
  async function fetchList() {
    if (!listinoId.value || !versioneId.value) return

    const f = filters.value
    const searchTerm = (f.search || '').trim()

    // Ricerca con meno di 3 caratteri: ignora (a meno che il campo sia vuoto).
    if (searchTerm.length > 0 && searchTerm.length < 3) return

    loading.value = true
    try {
      const params = {
        limit: f.limit,
        offset: f.offset,
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id

      const res = await listRighe(listinoId.value, versioneId.value, params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  return {
    items, totalRecords, loading,
    listinoId, versioneId,
    filters,
    setContext, clearContext, fetchList
  }
})
