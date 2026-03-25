// Pinia store per la gestione clienti (lista, creazione, dettaglio).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listClienti, getCliente, createCliente, updateCliente } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useClientiStore = defineStore('anagrafiche-clienti', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

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
  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
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
    emitDataChanged('cliente', res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del cliente.
  async function update(clienteId, payload) {
    const res = await updateCliente(clienteId, payload)
    emitDataChanged('cliente', clienteId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters,
    fetchList, fetchDetail, create, update
  }
})
