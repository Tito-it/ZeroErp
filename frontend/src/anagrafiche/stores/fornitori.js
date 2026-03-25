// Pinia store per la gestione fornitori (lista, creazione, dettaglio, aggiornamento).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listFornitori, getFornitore, createFornitore, updateFornitore } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useFornitoriStore = defineStore('anagrafiche-fornitori', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

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
  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
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
    emitDataChanged('fornitore', res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del fornitore.
  async function update(fornitoreId, payload) {
    const res = await updateFornitore(fornitoreId, payload)
    emitDataChanged('fornitore', fornitoreId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters,
    fetchList, fetchDetail, create, update
  }
})
