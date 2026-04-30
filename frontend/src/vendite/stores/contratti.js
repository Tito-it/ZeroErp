// Store Pinia contratti v5. Lista + detail + CRUD testata + azioni righe/utility + cambio stato.
// Filtro data obbligatorio (regola standard liste con date): data_da default anno-1.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listContratti, getContratto, createContratto, updateContratto, cambiaStatoContratto,
  addRigaContratto, updateRigaContratto, deleteRigaContratto, listRighePreviewContratto,
  addUtilityContratto, updateUtilityContratto,
} from '../api/contratti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

export const useContrattiStore = defineStore('vendite-contratti', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    billing_account_id: null,
    stato_doc_contratto_id: null,
    utility_id: null,
    ambito: null,
    listino_id: null,
    data_da: defaultDataDa,
    data_a: null,
    scadenza_mese: null,
    limit: 25,
    offset: 0,
    order_by: 'valido_dal',
    order_dir: 'desc',
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    loading.value = true
    try {
      const params = { limit: f.limit, offset: f.offset }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      if (f.stato_doc_contratto_id != null) params.stato_doc_contratto_id = f.stato_doc_contratto_id
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.ambito) params.ambito = f.ambito
      if (f.listino_id != null) params.listino_id = f.listino_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      if (f.scadenza_mese) params.scadenza_mese = f.scadenza_mese
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listContratti(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getContratto(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createContratto(payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateContratto(id, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
    return res.data.data
  }

  // `validoAl` opzionale (ISO YYYY-MM-DD): cessazione atomica con data.
  async function cambiaStato(id, codiceInterno, { validoAl = null } = {}) {
    const res = await cambiaStatoContratto(id, codiceInterno, { validoAl })
    emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
    return res.data.data
  }

  // Righe
  async function addRiga(contrattoId, payload) {
    const res = await addRigaContratto(contrattoId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }
  async function updateRiga(contrattoId, rigaId, payload) {
    const res = await updateRigaContratto(contrattoId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }
  async function deleteRiga(contrattoId, rigaId) {
    const res = await deleteRigaContratto(contrattoId, rigaId)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }

  // Anteprima righe applicate (modalita' A/B). Non emette tab event:
  // e' una read-only view che non muta il dominio.
  async function fetchRighePreview(contrattoId) {
    const res = await listRighePreviewContratto(contrattoId)
    return res.data.data
  }

  // Utility 1:1
  async function addUtility(contrattoId, payload) {
    const res = await addUtilityContratto(contrattoId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }
  async function updateUtility(contrattoId, utilityId, payload) {
    const res = await updateUtilityContratto(contrattoId, utilityId, payload)
    emitDataChanged(TAB_ENTITIES.CONTRATTO, contrattoId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, cambiaStato,
    addRiga, updateRiga, deleteRiga, fetchRighePreview,
    addUtility, updateUtility,
  }
}, {
  // Reset automatico al logout (autoResetPlugin): items + filters dell'utente
  // non devono persistere per l'eventuale utente successivo sullo stesso browser.
  userScoped: true,
})
