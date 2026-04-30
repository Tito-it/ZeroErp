// Store Pinia per la gestione tipologie UoM.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listUomTipi, getUomTipo, createUomTipo, updateUomTipo } from '../api/catalogo'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { TAB_ENTITIES } from '../../core/constants'
import { CATALOGO_LOOKUP_RELS } from '../constants'

export const useUomTipiStore = defineStore('catalogo-uom-tipi', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    attivo: true,
    limit: 25,
    offset: 0,
    order_by: 'descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    if (searchTerm.length > 0 && searchTerm.length < 3) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }

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
      if (f.attivo != null) params.attivo = f.attivo

      const res = await listUomTipi(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getUomTipo(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createUomTipo(payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UOM_TIPI)
    emitDataChanged(TAB_ENTITIES.UOM_TIPI, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateUomTipo(id, payload)
    invalidateLookup(CATALOGO_LOOKUP_RELS.UOM_TIPI)
    emitDataChanged(TAB_ENTITIES.UOM_TIPI, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
