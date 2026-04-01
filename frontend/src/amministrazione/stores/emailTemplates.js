// Pinia store per la gestione template email (lista, dettaglio, modifica).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listEmailTemplates,
  getEmailTemplate,
  updateEmailTemplate
} from '../api/amministrazione'

export const useEmailTemplatesStore = defineStore('amm-email-templates', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const currentTemplate = ref(null)
  const loadingDetail = ref(false)

  const filters = ref({
    search: '',
    limit: 25,
    offset: 0,
    order_by: 'codice',
    order_dir: 'asc'
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listEmailTemplates(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    loadingDetail.value = true
    try {
      const res = await getEmailTemplate(id)
      currentTemplate.value = res.data.data
    } finally {
      loadingDetail.value = false
    }
  }

  async function update(id, payload) {
    const res = await updateEmailTemplate(id, payload)
    currentTemplate.value = res.data.data
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters, fetchList,
    currentTemplate, loadingDetail, fetchDetail,
    update
  }
})
