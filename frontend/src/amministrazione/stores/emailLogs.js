// Pinia store per la consultazione log email (sola lettura).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listEmailLogs, getEmailLog } from '../api/amministrazione'

export const useEmailLogsStore = defineStore('amm-email-logs', () => {
  const currentLog = ref(null)
  const loadingDetail = ref(false)

  // Default data_da: 30 giorni fa
  const now = new Date()
  const thirtyDaysAgo = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30)
  const defaultDataDa = `${thirtyDaysAgo.getFullYear()}-${String(thirtyDaysAgo.getMonth() + 1).padStart(2, '0')}-${String(thirtyDaysAgo.getDate()).padStart(2, '0')}`

  const filters = ref({
    search: '',
    stato: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    order_by: 'data_insert',
    order_dir: 'desc'
  })

  // Lista via BB condiviso (migrazione 2026-08-10): la guardia di versione
  // anti-race che qui mancava. `alwaysFetch` conserva il comportamento: questa
  // lista si e' sempre caricata anche senza filtri.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f, _searchTerm) => {
      const params = {}
      if (f.search) params.search = f.search
      if (f.stato) params.stato = f.stato
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      return params
    },
    fetchPage: listEmailLogs,
  })

  async function fetchDetail(id) {
    loadingDetail.value = true
    try {
      const res = await getEmailLog(id)
      currentLog.value = res.data.data
    } finally {
      loadingDetail.value = false
    }
  }

  return {
    items, totalRecords, loading, hasSearched, filters, fetchList,
    currentLog, loadingDetail, fetchDetail
  }
}, { userScoped: true })
