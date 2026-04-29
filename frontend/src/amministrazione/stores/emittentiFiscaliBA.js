// Pinia store per lista paginata mapping BA -> emittente fiscale.
// Separato dallo store principale emittentiFiscali perche' la lista BA
// usa useSearchTable (contratto: filters, items, totalRecords, loading, fetchList).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listEmittenteBillingAccount,
  createEmittenteBillingAccount,
  deleteEmittenteBillingAccount,
  getEmittenteBillingAccountSummary
} from '../api/emittentiFiscali'

export const useEmittentiFiscaliBAStore = defineStore('amm-emittenti-fiscali-ba', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  // emittenteId corrente — settato dal tab quando cambia prop
  const emittenteId = ref(null)

  // Summary BA mapping (has_default + count_specifici): indipendente dalla
  // pagina corrente. Bypassa il bug della derivazione da `items` con liste
  // paginate. Aggiornato dopo ogni write + al cambio emittenteId.
  const hasDefaultMapping = ref(false)
  const countSpecifici = ref(0)

  const filters = ref({
    search: '',
    limit: 25,
    offset: 0,
    order_by: 'billing_account_codice',
    order_dir: 'asc'
  })

  async function fetchList() {
    if (!emittenteId.value) return
    loading.value = true
    try {
      const f = filters.value
      const params = {}
      if (f.search) params.search = f.search
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listEmittenteBillingAccount(emittenteId.value, params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  // Scopo: Carica il summary BA per l'emittente corrente. Best-effort:
  //        in caso di errore lascia i valori precedenti senza notificare
  //        (l'interceptor mostra l'errore HTTP, lo stato UX e' coerente).
  async function fetchSummary() {
    if (!emittenteId.value) {
      hasDefaultMapping.value = false
      countSpecifici.value = 0
      return
    }
    try {
      const res = await getEmittenteBillingAccountSummary(emittenteId.value)
      const data = res.data.data
      hasDefaultMapping.value = !!data.has_default
      countSpecifici.value = data.count_specifici || 0
    } catch {
      // Errore gia' notificato dall'interceptor axios globale.
    }
  }

  // Scopo: Aggiunge mapping e ricarica la lista + summary.
  async function addMapping(payload) {
    const res = await createEmittenteBillingAccount(emittenteId.value, payload)
    await Promise.all([fetchList(), fetchSummary()])
    return res.data.data
  }

  // Scopo: Elimina mapping e ricarica la lista + summary.
  async function removeMapping(mappingId) {
    await deleteEmittenteBillingAccount(emittenteId.value, mappingId)
    await Promise.all([fetchList(), fetchSummary()])
  }

  function reset() {
    items.value = []
    totalRecords.value = 0
    emittenteId.value = null
    hasDefaultMapping.value = false
    countSpecifici.value = 0
    filters.value.search = ''
    filters.value.offset = 0
  }

  return {
    items, totalRecords, loading, filters, emittenteId,
    hasDefaultMapping, countSpecifici,
    fetchList, fetchSummary, addMapping, removeMapping, reset
  }
})
