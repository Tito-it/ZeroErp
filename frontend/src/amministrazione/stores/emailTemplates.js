// Pinia store per la gestione template email (lista, dettaglio, modifica).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import {
  listEmailTemplates,
  getEmailTemplate,
  updateEmailTemplate
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useEmailTemplatesStore = defineStore('amm-email-templates', () => {
  const { emitDataChanged } = useTabEvents()

  const currentTemplate = ref(null)
  const loadingDetail = ref(false)

  const filters = ref({
    search: '',
    limit: 25,
    offset: 0,
    order_by: 'codice',
    order_dir: 'asc'
  })

  // Lista via BB condiviso (migrazione 2026-08-10): guardia di versione anti-race.
  // `alwaysFetch`: questa lista si e' sempre caricata anche senza filtri.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f) => {
      const params = {}
      if (f.search) params.search = f.search
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      return params
    },
    fetchPage: listEmailTemplates,
  })

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
    emitDataChanged(TAB_ENTITIES.EMAIL_TEMPLATES, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters, fetchList,
    currentTemplate, loadingDetail, fetchDetail,
    update
  }
}, { userScoped: true })
