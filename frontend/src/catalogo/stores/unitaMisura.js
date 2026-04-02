// Store Pinia per la gestione unita' di misura.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listUnitaMisura, getUnitaMisura, createUnitaMisura, updateUnitaMisura, disattivaUnitaMisura } from '../api/catalogo'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useUnitaMisuraStore = defineStore('catalogo-unita-misura', () => {
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
    order_by: 'codice',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    if (searchTerm.length > 0 && searchTerm.length < 3) return

    loading.value = true
    try {
      const params = {}
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo

      const res = await listUnitaMisura(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getUnitaMisura(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createUnitaMisura(payload)
    emitDataChanged('unita_misura', res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateUnitaMisura(id, payload)
    emitDataChanged('unita_misura', id)
    return res.data.data
  }

  async function disattiva(id) {
    const res = await disattivaUnitaMisura(id)
    emitDataChanged('unita_misura', id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, disattiva
  }
})
