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
import { buildDocListParams, hasDocListActiveFilters } from '../../_shared/listaDocumenti'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  cambiaStatoOrdine,
  confermaOrdine,
  createOrdine,
  createRiga,
  deleteOrdine,
  deleteRiga,
  emettiOrdine,
  getOrdine,
  getRiepilogoIva,
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
    hasActiveFilters: (f) => hasDocListActiveFilters(f, { withUtility: true }),
    buildParams: (f, searchTerm) => buildDocListParams(f, searchTerm, { withUtility: true }),
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

  // DRAFT -> CONFERMATO (sola transizione). Resta come API di servizio: il
  // flusso utente usa `emetti()` (apertura OrdineEmissioneDialog).
  async function conferma(id) {
    const res = await confermaOrdine(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // DRAFT -> CONFERMATO (multipart): conferma + genera documento + allegati in
  // transazione atomica lato BE. Invocata da OrdineEmissioneDialog (il drawer
  // intercetta l'action 'conferma' e apre il dialog invece di chiamare conferma).
  // Mirror del flusso emissione preventivo/offerta.
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiOrdine(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Push singolo a commessa (ordine CONFERMATO). Ritorna il report orchestrator.
  async function push(id) {
    const res = await pushOrdineACommessa(id)
    emitDataChanged(TAB_ENTITIES.ORDINE, id)
    return res.data.data
  }

  // Transizione di stato generica data-driven (es. annulla). `statoCodice` =
  // target_state dell'azione; il trigger DB valida l'ammissibilita'.
  async function cambiaStato(id, statoCodice) {
    const res = await cambiaStatoOrdine(id, statoCodice)
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

  // --- Riepilogo IVA ---

  // Scopo: Carica il riepilogo IVA aggregato dell'ordine (una entry per
  //        aliquota, regola fiscale DPR 633/72 art. 21). Calcolo derivato lato
  //        DB dalle righe attive: il FE legge solo lo stato corrente.
  async function loadRiepilogoIva(ordineId) {
    const res = await getRiepilogoIva(ordineId)
    return res.data.data
  }

  return {
    // state
    items, totalRecords, loading, hasSearched, filters,
    // testata
    fetchList, fetchDetail, create, update, elimina,
    // transizioni
    conferma, emetti, push, cambiaStato,
    // righe
    loadRighe, addRiga, aggiornaRiga, eliminaRiga,
    // riepilogo IVA
    loadRiepilogoIva,
  }
}, {
  userScoped: true,
})
