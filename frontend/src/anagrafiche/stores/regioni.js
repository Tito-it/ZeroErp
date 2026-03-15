// Pinia store per la gestione regioni (lista, CRUD).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listRegioni, createRegione, updateRegione } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useRegioniStore = defineStore('anagrafiche-regioni', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const filters = ref({
    search: '', stato_id: null,
    limit: 25, offset: 0, order_by: null, order_dir: null
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.stato_id != null) params.stato_id = f.stato_id
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) { params.order_by = f.order_by; params.order_dir = f.order_dir || 'asc' }
      const res = await listRegioni(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally { loading.value = false }
  }

  async function create(payload) {
    const res = await createRegione(payload)
    emitDataChanged('regione', res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateRegione(id, payload)
    emitDataChanged('regione', id)
    return res.data.data
  }

  return { items, totalRecords, loading, filters, fetchList, create, update }
})
