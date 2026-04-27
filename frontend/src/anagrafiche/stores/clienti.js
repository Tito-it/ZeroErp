// Pinia store per la gestione clienti (lista, creazione, dettaglio).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listClienti, getCliente, createCliente, updateCliente } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useClientiStore = defineStore('anagrafiche-clienti', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    utility_id: null,
    stato_cliente_id: null,
    limit: 25,
    offset: 0,
    order_by: 'ragione_sociale_completa',
    order_dir: 'asc'
  })

  // Scopo: Carica lista paginata clienti con filtri.
  // La lista parte vuota: richiede search (min 3 car) o filtro attivo.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.utility_id != null || f.stato_cliente_id != null

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
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.stato_cliente_id != null) params.stato_cliente_id = f.stato_cliente_id
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listClienti(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo cliente.
  async function fetchDetail(id) {
    const res = await getCliente(id)
    return res.data.data
  }

  // Scopo: Crea cliente completo (istanza + BA + cliente).
  async function create(payload) {
    const res = await createCliente(payload)
    emitDataChanged(TAB_ENTITIES.CLIENTE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del cliente.
  async function update(clienteId, payload) {
    const res = await updateCliente(clienteId, payload)
    emitDataChanged(TAB_ENTITIES.CLIENTE, clienteId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
