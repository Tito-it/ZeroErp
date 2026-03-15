// Pinia store per la gestione indirizzi dettaglio (lista, CRUD).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listIndirizzi, createIndirizzo, updateIndirizzo } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useIndirizziStore = defineStore('anagrafiche-indirizzi', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  const filters = ref({
    search: '',
    comune_id: null,
    limit: 25,
    offset: 0,
    order_by: null,
    order_dir: null
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.comune_id != null) params.comune_id = f.comune_id
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }

      const res = await listIndirizzi(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  async function create(payload) {
    const res = await createIndirizzo(payload)
    emitDataChanged('indirizzo', res.data.data.indirizzo_dettaglio_id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateIndirizzo(id, payload)
    emitDataChanged('indirizzo', id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters,
    fetchList, create, update
  }
})
