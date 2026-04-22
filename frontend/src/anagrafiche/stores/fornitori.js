// Pinia store per la gestione fornitori (lista, creazione, dettaglio, aggiornamento).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listFornitori, getFornitore, createFornitore, updateFornitore } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useFornitoriStore = defineStore('anagrafiche-fornitori', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    stato_fornitore_id: null,
    attivo: null,
    limit: 25,
    offset: 0,
    order_by: 'ragione_sociale_completa',
    order_dir: 'asc'
  })

  // Scopo: Carica lista paginata fornitori con filtri.
  // La lista parte vuota: richiede search (min 3 car) o filtro attivo.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.stato_fornitore_id != null || f.attivo != null

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
      if (f.stato_fornitore_id != null) params.stato_fornitore_id = f.stato_fornitore_id
      if (f.attivo != null) params.attivo = f.attivo
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listFornitori(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo fornitore.
  async function fetchDetail(id) {
    const res = await getFornitore(id)
    return res.data.data
  }

  // Scopo: Crea fornitore (ruolo FO + insert).
  async function create(payload) {
    const res = await createFornitore(payload)
    emitDataChanged(TAB_ENTITIES.FORNITORE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del fornitore.
  async function update(fornitoreId, payload) {
    const res = await updateFornitore(fornitoreId, payload)
    emitDataChanged(TAB_ENTITIES.FORNITORE, fornitoreId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
