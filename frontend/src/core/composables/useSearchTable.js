// Composable centralizzato per DataTable con ricerca, paginazione server-side e sort.
// Elimina la duplicazione di onPage/onSort/debounce search in ogni lista.
//
// Uso:
//   const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store)
//
// Nel template:
//   <DataTable v-bind="paginatorProps" lazy @page="onPage" @sort="onSort" ...>
//
// paginatorProps include: totalRecords, rows, first, rowsPerPageOptions,
//   paginator, paginatorTemplate, currentPageReportTemplate

import { ref, computed, watch, onUnmounted } from 'vue'
import { PAGINATION } from '../constants'

export function useSearchTable(store, options = {}) {
  const {
    debounceMs = 400,
    extraFilters = null // funzione che ritorna filtri aggiuntivi da applicare
  } = options

  const searchText = ref('')
  let searchTimeout = null

  // Debounce search → aggiorna store.filters.search e resetta offset
  watch(searchText, () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
      store.filters.search = searchText.value || ''
      store.filters.offset = 0
      store.fetchList()
    }, debounceMs)
  })

  // Cleanup timeout on unmount
  onUnmounted(() => { clearTimeout(searchTimeout) })

  // Handler @page DataTable — guard contro loop infinito e click rapidi.
  // PrimeVue DataTable ri-emette @page quando items cambia; senza guard si crea un ciclo.
  // Se una richiesta è in volo, ignora il click per evitare accavallamento risposte.
  function onPage(event) {
    if (event.first === store.filters.offset && event.rows === store.filters.limit) return
    if (store.loading) return
    store.filters.offset = event.first
    store.filters.limit = event.rows
    store.fetchList()
  }

  // Handler @sort DataTable
  function onSort(event) {
    store.filters.order_by = event.sortField
    store.filters.order_dir = event.sortOrder === 1 ? 'asc' : 'desc'
    store.fetchList()
  }

  // Applica filtri custom (chiamare quando cambiano filtri extra come comune_id)
  function applyFilters() {
    store.filters.search = searchText.value || ''
    store.filters.offset = 0
    if (extraFilters) {
      const extra = extraFilters()
      Object.assign(store.filters, extra)
    }
    store.fetchList()
  }

  // Props da passare al DataTable via v-bind
  const paginatorProps = computed(() => ({
    totalRecords: store.totalRecords,
    rows: store.filters.limit,
    first: store.filters.offset,
    rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
    paginator: true,
    paginatorPosition: 'top',
    paginatorTemplate: 'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown JumpToPageDropdown CurrentPageReport',
    currentPageReportTemplate: '{currentPage}/{totalPages}'
  }))

  return {
    searchText,
    onPage,
    onSort,
    applyFilters,
    paginatorProps
  }
}
