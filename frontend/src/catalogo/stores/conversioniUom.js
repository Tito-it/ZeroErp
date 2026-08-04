// Store Pinia per la gestione conversioni UoM.
// Paginazione, sort e search sono SERVER-SIDE (2026-08-01), come le due sorelle
// uomTipi/unitaMisura: prima caricava tutto e teneva `order_by` nei filtri senza
// mai inviarlo, quindi ordinare non faceva niente e il paginator era decorativo.
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
    // Regola di dominio (Tid, 2026-08-01): quando una lista mostra le date di
    // validita', `valido_al` E' l'ordinamento di default, in DESC. In Postgres
    // `DESC` porta i NULL in testa: prima le conversioni senza scadenza, poi
    // quelle con validita' piu' lunga, e in fondo le scadute — cioe' cio' che
    // vale ora sopra, cio' che non vale piu' sotto.
    //
    // ⚠️ Il preset del seed dichiara ancora `uom_from_codice asc`: allineamento
    // chiesto al team DB. Nessuno dei due e' letto dall'altro — il FE invia il
    // proprio `order_by` e `ordinamento_default` non e' ancora consumato —
    // quindi oggi vince questa riga.
    order_by: 'valido_al',
    order_dir: 'desc'
  })

  // Scopo: Carica la pagina corrente delle conversioni (server-side).
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    loading.value = true
    try {
      const params = {
        limit: f.limit,
        offset: f.offset,
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo

      const res = await listConversioniUom(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
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
