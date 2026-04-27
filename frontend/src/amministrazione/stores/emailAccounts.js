// Pinia store per la gestione account email (lista, dettaglio, CRUD).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listEmailAccounts,
  getEmailAccount,
  createEmailAccount,
  updateEmailAccount
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useEmailAccountsStore = defineStore('amm-email-accounts', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const currentAccount = ref(null)
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
      const res = await listEmailAccounts(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    loadingDetail.value = true
    try {
      const res = await getEmailAccount(id)
      currentAccount.value = res.data.data
    } finally {
      loadingDetail.value = false
    }
  }

  async function create(payload) {
    const res = await createEmailAccount(payload)
    emitDataChanged(TAB_ENTITIES.EMAIL_ACCOUNTS, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateEmailAccount(id, payload)
    currentAccount.value = res.data.data
    emitDataChanged(TAB_ENTITIES.EMAIL_ACCOUNTS, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, filters, fetchList,
    currentAccount, loadingDetail, fetchDetail,
    create, update
  }
})
