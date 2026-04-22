// Pinia store per la gestione soggetti (lista, CRUD, dettaglio).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listSoggetti, getSoggetto, createSoggetto, updateSoggetto
} from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useSoggettiStore = defineStore('anagrafiche-soggetti', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    tipo_soggetto_dettaglio_id: null,
    limit: 25,
    offset: 0,
    order_by: 'ragione_sociale_completa',
    order_dir: 'asc'
  })

  // Scopo: Carica lista paginata soggetti con filtri.
  // La lista parte vuota: richiede search (min 3 car) o filtro attivo.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.tipo_soggetto_dettaglio_id != null

    // Search con meno di 3 caratteri e nessun filtro attivo → svuota i
    // risultati precedenti (coerenza UX: niente dati obsoleti visibili).
    if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }
    if (!searchTerm && !hasFilters && !hasSearched.value) {
      return
    }
    // Search svuotata senza filtri → torna a stato vuoto
    if (!searchTerm && !hasFilters) {
      items.value = []
      totalRecords.value = 0
      hasSearched.value = false
      return
    }

    loading.value = true
    try {
      const params = {}
      if (searchTerm.length >= 3) params.search = searchTerm
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
      // Normalizza ruoli: il DB ritorna JSONB che può arrivare come stringa
      const results = res.data.data.results.map(r => ({
        ...r,
        ruoli: Array.isArray(r.ruoli) ? r.ruoli
          : (typeof r.ruoli === 'string' ? JSON.parse(r.ruoli) : [])
      }))
      items.value = results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
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
    emitDataChanged(TAB_ENTITIES.SOGGETTO, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi soggetto.
  async function update(id, payload) {
    const res = await updateSoggetto(id, payload)
    emitDataChanged(TAB_ENTITIES.SOGGETTO, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
