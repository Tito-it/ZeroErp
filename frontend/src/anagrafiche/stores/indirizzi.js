// Pinia store per la gestione indirizzi dettaglio (lista, CRUD).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listIndirizzi, createIndirizzo, updateIndirizzo } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useIndirizziStore = defineStore('anagrafiche-indirizzi', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    comune_id: null,
    limit: 25,
    offset: 0,
    order_by: null,
    order_dir: null
  })

  // Scopo: Carica lista paginata indirizzi con filtri.
  // La lista parte vuota: richiede search (min 3 car) o filtro attivo.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.comune_id != null

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
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function create(payload) {
    const res = await createIndirizzo(payload)
    emitDataChanged(TAB_ENTITIES.INDIRIZZO, res.data.data.indirizzo_dettaglio_id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateIndirizzo(id, payload)
    emitDataChanged(TAB_ENTITIES.INDIRIZZO, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, create, update
  }
})
