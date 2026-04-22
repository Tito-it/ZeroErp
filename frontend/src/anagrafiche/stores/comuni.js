// Pinia store per la gestione comuni (lista + creazione).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listComuni, createComune } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useComuniStore = defineStore('anagrafiche-comuni', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  const filters = ref({
    search: '',
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
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }

      const res = await listComuni(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  async function create(payload) {
    const res = await createComune(payload)
    emitDataChanged(TAB_ENTITIES.COMUNE, res.data.data.id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters,
    fetchList, create
  }
})
