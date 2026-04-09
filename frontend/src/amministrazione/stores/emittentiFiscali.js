// Pinia store per gestione emittenti fiscali (admin only).
// Lista, dettaglio, CRUD principale + sub-resource BA mapping e utilities.
// Pattern allineato a fornitori/operatori store: fetchDetail ritorna il dato,
// niente accesso al store dai consumatori del dettaglio (evita race condition).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listEmittentiFiscali,
  getEmittenteFiscale,
  createEmittenteFiscale,
  updateEmittenteFiscale,
  listEmittenteBillingAccount,
  createEmittenteBillingAccount,
  deleteEmittenteBillingAccount,
  listEmittenteUtilities,
  createEmittenteUtility,
  updateEmittenteUtility,
  deleteEmittenteUtility
} from '../api/emittentiFiscali'
import { useTabEvents } from '../../core/composables/useTabEvents'

const { emitDataChanged } = useTabEvents()

export const useEmittentiFiscaliStore = defineStore('amm-emittenti-fiscali', () => {
  // Lista
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  // Sub-resource: caricati on demand dai tab e tenuti qui per evitare di passare
  // ref dai componenti padre. I tab puliscono lo state in unmount/reload.
  const billingAccountMappings = ref([])
  const utilitiesRecords = ref([])

  const filters = ref({
    search: '',
    attivo: null,
    limit: 25,
    offset: 0,
    order_by: 'descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.attivo != null) params.attivo = f.attivo
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'ASC'
      }
      const res = await listEmittentiFiscali(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo emittente (ritorna il dato, non lo conserva nello store).
  async function fetchDetail(id) {
    const res = await getEmittenteFiscale(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createEmittenteFiscale(payload)
    emitDataChanged('emittente-fiscale', res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateEmittenteFiscale(id, payload)
    emitDataChanged('emittente-fiscale', id)
    return res.data.data
  }

  // --- Sub-resource: mapping BA ---

  async function fetchBillingAccountMappings(emittenteId) {
    const res = await listEmittenteBillingAccount(emittenteId)
    billingAccountMappings.value = res.data.data.results
  }

  function clearBillingAccountMappings() {
    billingAccountMappings.value = []
  }

  async function addBillingAccountMapping(emittenteId, payload) {
    const res = await createEmittenteBillingAccount(emittenteId, payload)
    await fetchBillingAccountMappings(emittenteId)
    return res.data.data
  }

  async function removeBillingAccountMapping(emittenteId, mappingId) {
    await deleteEmittenteBillingAccount(emittenteId, mappingId)
    await fetchBillingAccountMappings(emittenteId)
  }

  // --- Sub-resource: utilities ---

  async function fetchUtilitiesRecords(emittenteId) {
    const res = await listEmittenteUtilities(emittenteId)
    utilitiesRecords.value = res.data.data.results
  }

  function clearUtilitiesRecords() {
    utilitiesRecords.value = []
  }

  async function addUtilityRecord(emittenteId, payload) {
    const res = await createEmittenteUtility(emittenteId, payload)
    await fetchUtilitiesRecords(emittenteId)
    return res.data.data
  }

  async function patchUtilityRecord(emittenteId, recordId, payload) {
    const res = await updateEmittenteUtility(emittenteId, recordId, payload)
    await fetchUtilitiesRecords(emittenteId)
    return res.data.data
  }

  async function removeUtilityRecord(emittenteId, recordId) {
    await deleteEmittenteUtility(emittenteId, recordId)
    await fetchUtilitiesRecords(emittenteId)
  }

  return {
    // Lista
    items, totalRecords, loading, filters, fetchList,
    // CRUD
    fetchDetail, create, update,
    // BA mapping
    billingAccountMappings,
    fetchBillingAccountMappings,
    clearBillingAccountMappings,
    addBillingAccountMapping,
    removeBillingAccountMapping,
    // Utilities
    utilitiesRecords,
    fetchUtilitiesRecords,
    clearUtilitiesRecords,
    addUtilityRecord,
    patchUtilityRecord,
    removeUtilityRecord
  }
})
