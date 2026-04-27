// Store Pinia per la gestione della matrice config.utilities_tipi_ruolo (admin).
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listUtilitiesTipiRuolo,
  getUtilityTipoRuolo,
  createUtilityTipoRuolo,
  updateUtilityTipoRuolo,
  listUtilityTipoRuoloUsage
} from '../api/utilitiesTipiRuolo'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useUtilitiesTipiRuoloStore = defineStore('amministrazione-utilities-tipi-ruolo', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    attivo: true,
    utility_id: null,
    tipo_ruolo_id: null,
    limit: 25,
    offset: 0,
    order_by: 'utility_descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    // Stesso pattern di unita_misura: search opzionale ma min 3 caratteri se presente
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
        offset: f.offset
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.tipo_ruolo_id != null) params.tipo_ruolo_id = f.tipo_ruolo_id

      const res = await listUtilitiesTipiRuolo(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getUtilityTipoRuolo(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createUtilityTipoRuolo(payload)
    emitDataChanged(TAB_ENTITIES.UTILITIES_TIPI_RUOLO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateUtilityTipoRuolo(id, payload)
    emitDataChanged(TAB_ENTITIES.UTILITIES_TIPI_RUOLO, id)
    return res.data.data
  }

  async function fetchUsage(id, params = {}) {
    const res = await listUtilityTipoRuoloUsage(id, params)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, fetchUsage
  }
})
