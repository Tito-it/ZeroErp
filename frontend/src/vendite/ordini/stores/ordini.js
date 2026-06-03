// Store Pinia per gli ordini di vendita (lista, dettaglio, CRUD testata,
// righe, conferma, push singolo a commessa).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser (memoria feedback_pinia_userscoped).
//
// Niente revisioni ne' listino in testata (a differenza di preventivi/offerte):
// gli ordini fissano i prezzi alle righe alla conferma.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaEmptyStateFetch } from '../../../core/composables/useListaEmptyStateFetch'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  confermaOrdine,
  createOrdine,
  createRiga,
  deleteOrdine,
  deleteRiga,
  getOrdine,
  listOrdini,
  listRighe,
  pushOrdineACommessa,
  updateOrdine,
  updateRiga,
} from '../api/ordiniApi'

export const useOrdiniStore = defineStore('vendite-ordini', () => {
  const { emitDataChanged } = useTabEvents()

  // Default data_da: 1 gennaio anno corrente - 1 (frontend-standards "Filtro
  // data standard"): la lista parte popolata sull'ultimo anno + anno corrente.
  const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

  const filters = ref({
    search: '',
    stato_codice_interno: null,
    billing_account_id: null,
    utility_id: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    // Default `data desc`: ordini con data piu' recente in cima (allineato al
    // default backend e al defaultSortField della OrdiniSearchTable).
    order_by: 'data',
    order_dir: 'desc',
  })

  // Lista paginata ordini con guardia empty-state standard (BB
  // useListaEmptyStateFetch). `data_da` default-anno-1 conta come filtro attivo:
  // la lista si popola al mount. Ordini usa limit/offset (non page/page_size).
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    hasActiveFilters: (f) => f.stato_codice_interno != null
      || f.billing_account_id != null
      || f.utility_id != null
      || f.data_a != null
      || f.data_da != null,
    buildParams: (f, searchTerm) => {
      const params = {}
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.stato_codice_interno != null) params.stato_codice_interno = f.stato_codice_interno
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      params.limit = f.limit || 25
      params.offset = f.offset || 0
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      return params
    },
    fetchPage: listOrdini,
  })

  // Scopo: Dettaglio testata ordine + capability (righe_count, can_edit_*,
  //        can_conferma, can_push_commessa).
  async function fetchDetail(id) {
    const res = await getOrdine(id)
    return res.data.data
  }

  // Scopo: Crea nuovo ordine BOZZA. Il numero arriva dal trigger DB.
  async function create(payload) {
    const res = await createOrdine(payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata ordine (solo in DRAFT).
  async function update(id, payload) {
    const res = await updateOrdine(id, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Scopo: Hard-delete ordine BOZZA orfano (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteOrdine(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // --- Transizioni / integrazione ---

  // DRAFT -> CONFERMATO.
  async function conferma(id) {
    const res = await confermaOrdine(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Push singolo a commessa (ordine CONFERMATO). Ritorna il report orchestrator.
  async function push(id) {
    const res = await pushOrdineACommessa(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // --- Righe ---

  async function loadRighe(ordineId) {
    const res = await listRighe(ordineId)
    return res.data.data
  }

  async function addRiga(ordineId, payload) {
    const res = await createRiga(ordineId, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  async function aggiornaRiga(ordineId, rigaId, payload) {
    const res = await updateRiga(ordineId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  async function eliminaRiga(ordineId, rigaId) {
    const res = await deleteRiga(ordineId, rigaId)
    emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
    return res.data.data
  }

  return {
    // state
    items, totalRecords, loading, hasSearched, filters,
    // testata
    fetchList, fetchDetail, create, update, elimina,
    // transizioni
    conferma, push,
    // righe
    loadRighe, addRiga, aggiornaRiga, eliminaRiga,
  }
}, {
  userScoped: true,
})
