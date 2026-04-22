// Store Pinia per la gestione conversioni UoM.
// Dataset piccolo: carica tutto dal backend, paginazione/sort/search client-side via useSearchTable.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listConversioniUom, getConversioneUom, createConversioneUom, updateConversioneUom } from '../api/catalogo'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useConversioniUomStore = defineStore('catalogo-conversioni-uom', () => {
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
    order_by: 'uom_from_descrizione',
    order_dir: 'asc'
  })

  // Scopo: Carica tutte le conversioni dal backend.
  //        Paginazione e sort sono gestiti client-side da PrimeVue DataTable.
  async function fetchList() {
    loading.value = true
    try {
      const res = await listConversioniUom()
      items.value = res.data.data || []
      totalRecords.value = items.value.length
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getConversioneUom(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createConversioneUom(payload)
    emitDataChanged(TAB_ENTITIES.CONVERSIONI_UOM, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateConversioneUom(id, payload)
    emitDataChanged(TAB_ENTITIES.CONVERSIONI_UOM, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update
  }
})
