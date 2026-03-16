// Pinia store per la gestione soggetti (lista, CRUD, dettaglio).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listSoggetti, getSoggetto, createSoggetto, updateSoggetto
} from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useSoggettiStore = defineStore('anagrafiche-soggetti', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  const filters = ref({
    search: '',
    tipo_soggetto_dettaglio_id: null,
    limit: 25,
    offset: 0,
    order_by: null,
    order_dir: null
  })

  // Scopo: Carica lista paginata soggetti con filtri.
  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.tipo_soggetto_dettaglio_id != null) {
        params.tipo_soggetto_dettaglio_id = f.tipo_soggetto_dettaglio_id
      }
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }

      const res = await listSoggetti(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio soggetto completo (contatti, indirizzi, ruoli, dati societari).
  async function fetchDetail(id) {
    const res = await getSoggetto(id)
    return res.data.data
  }

  // Scopo: Crea soggetto completo (PF o PG + contatto + indirizzi).
  async function create(payload) {
    const res = await createSoggetto(payload)
    emitDataChanged('soggetto', res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi soggetto.
  async function update(id, payload) {
    const res = await updateSoggetto(id, payload)
    emitDataChanged('soggetto', id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters,
    fetchList, fetchDetail, create, update
  }
})
