// Store Pinia per la gestione listini vendite.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listListini, getListino, createListino, updateListino } from '../api/listini'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useListiniStore = defineStore('vendite-listini', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    dominio: null,
    attivo: true,
    limit: 25,
    offset: 0,
    order_by: 'descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    if (searchTerm.length > 0 && searchTerm.length < 3) return

    loading.value = true
    try {
      const params = {}
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.dominio != null) params.dominio = f.dominio
      if (f.attivo != null) params.attivo = f.attivo

      const res = await listListini(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getListino(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createListino(payload)
    emitDataChanged('listino', res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateListino(id, payload)
    emitDataChanged('listino', id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
