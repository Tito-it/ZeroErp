// Pinia store per lista paginata mapping BA -> emittente fiscale.
// Separato dallo store principale emittentiFiscali perche' la lista BA
// usa useSearchTable (contratto: filters, items, totalRecords, loading, fetchList).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listEmittenteBillingAccount,
  createEmittenteBillingAccount,
  deleteEmittenteBillingAccount
} from '../api/emittentiFiscali'

export const useEmittentiFiscaliBAStore = defineStore('amm-emittenti-fiscali-ba', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  // emittenteId corrente — settato dal tab quando cambia prop
  const emittenteId = ref(null)

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

  // Scopo: Aggiunge mapping e ricarica la lista.
  async function addMapping(payload) {
    const res = await createEmittenteBillingAccount(emittenteId.value, payload)
    await fetchList()
    return res.data.data
  }

  // Scopo: Elimina mapping e ricarica la lista.
  async function removeMapping(mappingId) {
    await deleteEmittenteBillingAccount(emittenteId.value, mappingId)
    await fetchList()
  }

  function reset() {
    items.value = []
    totalRecords.value = 0
    emittenteId.value = null
    filters.value.search = ''
    filters.value.offset = 0
  }

  return {
    items, totalRecords, loading, filters, emittenteId,
    fetchList, addMapping, removeMapping, reset
  }
})
