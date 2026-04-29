// Store Pinia per la gestione articoli catalogo.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listArticoli, getArticolo, createArticolo, updateArticolo, disattivaArticolo, riattivaArticolo } from '../api/catalogo'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useArticoliStore = defineStore('catalogo-articoli', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

  const filters = ref({
    search: '',
    attivo: true,
    is_composito: null,
    tipo_voce_id: null,
    gruppo_voce_id: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    order_by: 'descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.is_composito != null ||
      f.tipo_voce_id != null || f.gruppo_voce_id != null ||
      f.data_da != null || f.data_a != null

    if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }
    if (!searchTerm && !hasFilters && !hasSearched.value) return
    if (!searchTerm && !hasFilters) {
      items.value = []
      totalRecords.value = 0
      hasSearched.value = false
      return
    }

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
      if (f.attivo != null) params.attivo = f.attivo
      if (f.is_composito != null) params.is_composito = f.is_composito
      if (f.tipo_voce_id != null) params.tipo_voce_id = f.tipo_voce_id
      if (f.gruppo_voce_id != null) params.gruppo_voce_id = f.gruppo_voce_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a

      const res = await listArticoli(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getArticolo(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createArticolo(payload)
    emitDataChanged(TAB_ENTITIES.ARTICOLO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateArticolo(id, payload)
    emitDataChanged(TAB_ENTITIES.ARTICOLO, id)
    return res.data.data
  }

  async function disattiva(id) {
    const res = await disattivaArticolo(id)
    emitDataChanged(TAB_ENTITIES.ARTICOLO, id)
    return res.data.data
  }

  async function riattiva(id) {
    const res = await riattivaArticolo(id)
    emitDataChanged(TAB_ENTITIES.ARTICOLO, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, disattiva, riattiva
  }
})
