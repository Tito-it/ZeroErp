// Pinia store per la consultazione log email (sola lettura).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listEmailLogs, getEmailLog } from '../api/amministrazione'

export const useEmailLogsStore = defineStore('amm-email-logs', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
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

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
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
      const res = await listEmailLogs(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

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
    items, totalRecords, loading, filters, fetchList,
    currentLog, loadingDetail, fetchDetail
  }
})
