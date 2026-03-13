// Pinia store per la gestione utenti (lista, dettaglio, CRUD).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listUtenti,
  getUtente,
  createUtente,
  updateUtente,
  disabilitaUtente,
  getOverrideAree,
  putOverrideAree,
  getOverrideAzioni,
  putOverrideAzioni,
  getEmittentiScope,
  putEmittentiScope,
  listUnitaOrganizzative,
  listAreeFunzionali,
  listAzioniProcesso,
  listEmittentiFiscali
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'

const { emitDataChanged } = useTabEvents()

export const useUtentiStore = defineStore('amm-utenti', () => {
  // Lista
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  // Dettaglio/corrente
  const currentUtente = ref(null)
  const loadingDetail = ref(false)

  // Filtri attivi (sincronizzati con la toolbar)
  const filters = ref({
    search: '',
    ruolo_sistema: null,
    unita_organizzativa_id: null,
    is_active: null,
    limit: 25,
    offset: 0,
    order_by: null,
    order_dir: null
  })

  // Lookup cache
  const unitaOrganizzative = ref([])
  const areeFunzionali = ref([])
  const azioniProcesso = ref([])
  const emittentiFiscali = ref([])

  // Override corrente
  const overrideAree = ref([])
  const overrideAzioni = ref([])
  const emittentiScope = ref([])

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.ruolo_sistema) params.ruolo_sistema = f.ruolo_sistema
      if (f.unita_organizzativa_id != null) params.unita_organizzativa_id = f.unita_organizzativa_id
      if (f.is_active != null) params.is_active = f.is_active
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'ASC'
      }

      const res = await listUtenti(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(authUserId) {
    loadingDetail.value = true
    try {
      const res = await getUtente(authUserId)
      currentUtente.value = res.data.data
    } finally {
      loadingDetail.value = false
    }
  }

  async function create(payload) {
    const res = await createUtente(payload)
    const created = res.data.data
    emitDataChanged('utente', created.auth_user_id)
    return created
  }

  async function update(authUserId, payload) {
    const res = await updateUtente(authUserId, payload)
    currentUtente.value = res.data.data
    emitDataChanged('utente', authUserId)
    return res.data.data
  }

  async function disabilita(authUserId) {
    const res = await disabilitaUtente(authUserId)
    currentUtente.value = res.data.data
    emitDataChanged('utente', authUserId)
    return res.data.data
  }

  // --- Override aree ---
  async function fetchOverrideAree(authUserId) {
    const res = await getOverrideAree(authUserId)
    overrideAree.value = res.data.data.results
  }

  async function saveOverrideAree(authUserId, items) {
    const res = await putOverrideAree(authUserId, items)
    overrideAree.value = res.data.data.results
    emitDataChanged('utente', authUserId)
  }

  // --- Override azioni ---
  async function fetchOverrideAzioni(authUserId) {
    const res = await getOverrideAzioni(authUserId)
    overrideAzioni.value = res.data.data.results
  }

  async function saveOverrideAzioni(authUserId, items) {
    const res = await putOverrideAzioni(authUserId, items)
    overrideAzioni.value = res.data.data.results
    emitDataChanged('utente', authUserId)
  }

  // --- Emittenti scope ---
  async function fetchEmittentiScope(authUserId) {
    const res = await getEmittentiScope(authUserId)
    emittentiScope.value = res.data.data.results
  }

  async function saveEmittentiScope(authUserId, emittenteIds) {
    const res = await putEmittentiScope(authUserId, emittenteIds)
    emittentiScope.value = res.data.data.results
    emitDataChanged('utente', authUserId)
  }

  // --- Lookup ---
  async function fetchUnitaOrganizzative() {
    if (unitaOrganizzative.value.length) return
    const res = await listUnitaOrganizzative()
    unitaOrganizzative.value = res.data.data.results
  }

  async function fetchAreeFunzionali() {
    if (areeFunzionali.value.length) return
    const res = await listAreeFunzionali()
    areeFunzionali.value = res.data.data.results
  }

  async function fetchAzioniProcesso() {
    if (azioniProcesso.value.length) return
    const res = await listAzioniProcesso()
    azioniProcesso.value = res.data.data.results
  }

  async function fetchEmittentiFiscali() {
    if (emittentiFiscali.value.length) return
    const res = await listEmittentiFiscali()
    emittentiFiscali.value = res.data.data.results
  }

  return {
    // Lista
    items,
    totalRecords,
    loading,
    filters,
    fetchList,

    // Dettaglio
    currentUtente,
    loadingDetail,
    fetchDetail,

    // CRUD
    create,
    update,
    disabilita,

    // Override
    overrideAree,
    overrideAzioni,
    emittentiScope,
    fetchOverrideAree,
    saveOverrideAree,
    fetchOverrideAzioni,
    saveOverrideAzioni,
    fetchEmittentiScope,
    saveEmittentiScope,

    // Lookup
    unitaOrganizzative,
    areeFunzionali,
    azioniProcesso,
    emittentiFiscali,
    fetchUnitaOrganizzative,
    fetchAreeFunzionali,
    fetchAzioniProcesso,
    fetchEmittentiFiscali
  }
})
