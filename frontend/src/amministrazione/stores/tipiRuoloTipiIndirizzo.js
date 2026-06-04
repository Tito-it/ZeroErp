// Store Pinia per la gestione della matrice config.tipi_ruolo_tipi_indirizzo (admin).
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listTipiRuoloTipiIndirizzo,
  getTipoRuoloTipoIndirizzo,
  createTipoRuoloTipoIndirizzo,
  updateTipoRuoloTipoIndirizzo
} from '../api/tipiRuoloTipiIndirizzo'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useTipiRuoloTipiIndirizzoStore = defineStore('amministrazione-tipi-ruolo-tipi-indirizzo', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    attivo: true,
    tipo_ruolo_id: null,
    tipo_indirizzo_id: null,
    limit: 25,
    offset: 0,
    order_by: 'tipo_ruolo_descrizione',
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
        offset: f.offset
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo
      if (f.tipo_ruolo_id != null) params.tipo_ruolo_id = f.tipo_ruolo_id
      if (f.tipo_indirizzo_id != null) params.tipo_indirizzo_id = f.tipo_indirizzo_id

      const res = await listTipiRuoloTipiIndirizzo(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getTipoRuoloTipoIndirizzo(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createTipoRuoloTipoIndirizzo(payload)
    emitDataChanged(TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateTipoRuoloTipoIndirizzo(id, payload)
    emitDataChanged(TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
}, { userScoped: true })
