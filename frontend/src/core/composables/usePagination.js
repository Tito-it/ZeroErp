// Composable per paginazione server-side.
// Gestisce stato pagina, righe per pagina, totale record, e integra con PrimeVue DataTable.
//
// Uso:
//   const pagination = usePagination()
//   // nella chiamata API:
//   const params = { ...pagination.queryParams.value, search: ... }
//   const data = await execute(() => api.get('/endpoint/', { params }))
//   pagination.updateFromResponse(data)
//
//   // nel template DataTable:
//   <DataTable :value="items" lazy :totalRecords="pagination.totalRecords.value"
//     :rows="pagination.rows.value" @page="pagination.onPage">

import { ref, computed } from 'vue'
import { misureOpzioni, misuraPerViewport } from '../misurePagina'

export function usePagination(options = {}) {
  const page = ref(1)
  const rows = ref(options.rows || misuraPerViewport())
  const totalRecords = ref(0)
  const totalPages = computed(() => Math.max(1, Math.ceil(totalRecords.value / rows.value)))

  // Parametri query da inviare all'API backend: la FINESTRA `limit`/`offset`
  // (2026-10-21, un dialetto solo: il backend rifiuta `page`/`page_size`).
  const queryParams = computed(() => ({
    limit: rows.value,
    offset: (page.value - 1) * rows.value
  }))

  // Aggiorna lo stato dalla risposta API (formato DRF: { count, results })
  function updateFromResponse(data) {
    if (!data) return
    if (typeof data.count === 'number') {
      totalRecords.value = data.count
    }
  }

  // Handler evento @page di PrimeVue DataTable
  function onPage(event) {
    page.value = Math.floor(event.first / event.rows) + 1
    rows.value = event.rows
  }

  // Offset calcolato per PrimeVue DataTable (prop :first)
  const first = computed(() => (page.value - 1) * rows.value)

  // Vai a una pagina specifica (con validazione)
  function goToPage(targetPage) {
    const p = Number(targetPage)
    if (!Number.isFinite(p) || p < 1) {
      page.value = 1
    } else if (p > totalPages.value) {
      page.value = totalPages.value
    } else {
      page.value = p
    }
  }

  // Reset alla prima pagina (utile quando cambiano i filtri)
  function reset() {
    page.value = 1
    totalRecords.value = 0
  }

  return {
    page,
    rows,
    totalRecords,
    totalPages,
    first,
    queryParams,
    rowsOptions: misureOpzioni(),
    onPage,
    goToPage,
    reset,
    updateFromResponse
  }
}
