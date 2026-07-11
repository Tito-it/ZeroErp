// Store Pinia per i DDT di vendita (lista, dettaglio, CRUD testata, righe,
// emissione, cambio stato data-driven, push singolo a commessa).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser (memoria feedback_pinia_userscoped).
//
// Clone strutturale di stores/ordini (analisi-ddt-vendita §D-4). Differenze:
// niente conferma (l'emissione DDT non genera documento in questa slice, il
// numero lo assegna il trigger a EMESSO) e niente riepilogo IVA (fuori scope,
// nessun endpoint BE). L'evasione (genera DDT da ordine) vive nel dominio
// ordine, non qui.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaEmptyStateFetch } from '../../../core/composables/useListaEmptyStateFetch'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  cambiaStatoDdt,
  createDdt,
  createRiga,
  deleteDdt,
  deleteRiga,
  emettiDdt,
  getDdt,
  getRiepilogoIva,
  listDdt,
  listRighe,
  pushDdtACommessa,
  updateDdt,
  updateRiga,
} from '../api/ddtApi'

export const useDdtStore = defineStore('vendite-ddt', () => {
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
    // Default `data desc`: DDT con data piu' recente in cima (allineato al
    // default backend e al defaultSortField della DdtSearchTable).
    order_by: 'data',
    order_dir: 'desc',
  })

  // Lista paginata DDT con guardia empty-state standard (BB
  // useListaEmptyStateFetch). `data_da` default-anno-1 conta come filtro attivo:
  // la lista si popola al mount. Il DDT usa limit/offset (non page/page_size).
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
    fetchPage: listDdt,
  })

  // Scopo: Dettaglio testata DDT + capability (righe_count, can_edit_*,
  //        can_change_state, can_push_commessa, available_actions,
  //        non_editable_fields, stato_codice).
  async function fetchDetail(id) {
    const res = await getDdt(id)
    return res.data.data
  }

  // Scopo: Crea nuovo DDT standalone BOZZA. Il numero arriva dal trigger DB solo
  //        a EMESSO (in DRAFT resta NULL).
  async function create(payload) {
    const res = await createDdt(payload)
    emitDataChanged(TAB_ENTITIES.DDT, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata DDT (solo in DRAFT).
  async function update(id, payload) {
    const res = await updateDdt(id, payload)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Scopo: Hard-delete DDT BOZZA orfano (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteDdt(id)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // --- Transizioni / integrazione ---

  // DRAFT -> EMESSO (multipart): assegna il numero (trigger DB) + gate
  // approvazione componenti + genera il documento accompagnatorio (+ allegati
  // opzionali) in transazione atomica lato BE. Mirror di ordini.emetti.
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiDdt(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Transizione di stato generica data-driven (SPEDITO/CONSEGNATO/RESO/ANNULLATO).
  // `statoCodice` = target_state dell'azione; il trigger DB valida l'ammissibilita'.
  async function cambiaStato(id, statoCodice) {
    const res = await cambiaStatoDdt(id, statoCodice)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Push singolo a commessa (DDT SPEDITO/CONSEGNATO). Ritorna il report orchestrator.
  async function push(id) {
    const res = await pushDdtACommessa(id)
    emitDataChanged(TAB_ENTITIES.DDT, id)
    return res.data.data
  }

  // Scopo: Carica il riepilogo IVA aggregato del DDT (una entry per aliquota,
  //        regola fiscale DPR 633/72 art. 21). Calcolo derivato lato DB dalle
  //        righe attive valorizzate: il FE legge solo lo stato corrente.
  async function loadRiepilogoIva(ddtId) {
    const res = await getRiepilogoIva(ddtId)
    return res.data.data
  }

  // --- Righe ---

  async function loadRighe(ddtId) {
    const res = await listRighe(ddtId)
    return res.data.data
  }

  async function addRiga(ddtId, payload) {
    const res = await createRiga(ddtId, payload)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  async function aggiornaRiga(ddtId, rigaId, payload) {
    const res = await updateRiga(ddtId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  async function eliminaRiga(ddtId, rigaId) {
    const res = await deleteRiga(ddtId, rigaId)
    emitDataChanged(TAB_ENTITIES.DDT, ddtId)
    return res.data.data
  }

  return {
    // state
    items, totalRecords, loading, hasSearched, filters,
    // testata
    fetchList, fetchDetail, create, update, elimina,
    // transizioni
    emetti, cambiaStato, push,
    // riepilogo IVA
    loadRiepilogoIva,
    // righe
    loadRighe, addRiga, aggiornaRiga, eliminaRiga,
  }
}, {
  userScoped: true,
})
