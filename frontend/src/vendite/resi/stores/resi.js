// Store Pinia per i resi di vendita (lista, dettaglio, CRUD testata/righe,
// conferma/annullo, generazione DDT di ri-consegna, code di lavoro).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser (memoria feedback_pinia_userscoped).
//
// Clone strutturale ridotto di stores/ddt (brief-be-fe-resi-vendita §10):
// niente emissione/push/riepilogo IVA/utility; in piu' le azioni di dominio
// dedicate (le fn madri DB applicano gli effetti — mai UPDATE di stato nudo).
// Le due code (vw_resi_da_*) sono consumate da ResiCodaTable direttamente
// via API + usePagedDashFetch (stato pagina locale al componente).

import { defaultFiltroDataDaString } from '../../../core/utils/date'
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaEmptyStateFetch } from '../../../core/composables/useListaEmptyStateFetch'
import { buildDocListParams, hasDocListActiveFilters } from '../../_shared/listaDocumenti'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  annullaReso,
  confermaReso,
  createReso,
  createRiga,
  deleteReso,
  deleteRiga,
  chiudiRiconsegna as apiChiudiRiconsegna,
  generaDdtRiconsegna,
  riapriRiconsegna as apiRiapriRiconsegna,
  getReso,
  listResi,
  listRighe,
  updateReso,
  updateRiga,
} from '../api/resiApi'

export const useResiStore = defineStore('vendite-resi', () => {
  const { emitDataChanged } = useTabEvents()

  // Floor temporale di default delle liste: vedi `defaultFiltroDataDaString`
  // (oggi-60gg al primo del mese). Regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  const filters = ref({
    search: '',
    stato_codice_interno: null,
    billing_account_id: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    // Default `data desc`: resi con data piu' recente in cima (allineato al
    // default backend e al defaultSortField della ResiSearchTable).
    order_by: 'data',
    order_dir: 'desc',
  })

  // Lista paginata resi con guardia empty-state standard (BB
  // useListaEmptyStateFetch). `data_da` col default standard conta come filtro
  // attivo: la lista si popola al mount. limit/offset come DDT/ordini.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    hasActiveFilters: (f) => hasDocListActiveFilters(f),
    buildParams: (f, searchTerm) => buildDocListParams(f, searchTerm),
    fetchPage: listResi,
  })

  // Scopo: Dettaglio testata reso + capability (righe_count, can_edit_*,
  //        available_actions, non_editable_fields, stato_codice).
  async function fetchDetail(id) {
    const res = await getReso(id)
    return res.data.data
  }

  // Scopo: Crea reso da DDT (DRAFT), con eventuali righe in transazione
  //        (pannello "crea reso" del drawer DDT).
  async function create(payload) {
    const res = await createReso(payload)
    emitDataChanged(TAB_ENTITIES.RESO, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata reso (solo DRAFT; data/meta).
  async function update(id, payload) {
    const res = await updateReso(id, payload)
    emitDataChanged(TAB_ENTITIES.RESO, id)
    return res.data.data
  }

  // Scopo: Hard-delete reso BOZZA orfano (abbandono bozza senza righe).
  async function elimina(id) {
    const res = await deleteReso(id)
    emitDataChanged(TAB_ENTITIES.RESO, id)
    return res.data.data
  }

  // --- Azioni di dominio (fn madri DB) ---

  // DRAFT -> CONFERMATO: numero assegnato dal trigger; riapertura residuo
  // ordine + proiezione stato + eventuale flip DDT->RESO (reso totale).
  // Notifica anche i tab DDT e ORDINE: i loro stati possono essere cambiati.
  async function conferma(id) {
    const res = await confermaReso(id)
    emitDataChanged(TAB_ENTITIES.RESO, id)
    emitDataChanged(TAB_ENTITIES.DDT, null)
    emitDataChanged(TAB_ENTITIES.ORDINE, null)
    return res.data.data
  }

  // Annullo (da DRAFT o CONFERMATO, storno effetti post-conferma).
  async function annulla(id) {
    const res = await annullaReso(id)
    emitDataChanged(TAB_ENTITIES.RESO, id)
    emitDataChanged(TAB_ENTITIES.DDT, null)
    emitDataChanged(TAB_ENTITIES.ORDINE, null)
    return res.data.data
  }

  // Genera il DDT di ri-consegna (righe [{resi_riga_id, qta}] in unita' BASE;
  // null = tutta la copertura residua). Il DDT nasce in DRAFT nel tab DDT.
  async function generaRiconsegna(id, { righe = null, data = null } = {}) {
    const res = await generaDdtRiconsegna(id, { righe, data })
    emitDataChanged(TAB_ENTITIES.RESO, id)
    emitDataChanged(TAB_ENTITIES.DDT, res.data.data?.ddt_id ?? null)
    return res.data.data
  }

  // Chiude la ri-consegna (rinuncia): la quota resa diventa definitiva, il
  // residuo ordine si chiude e l'accredito passa a DOVUTA. Notifica anche
  // l'ORDINE: il suo stato cambia (→ EVASO) come effetto collaterale, ed e' il
  // caso che il refresh KeepAlive delle liste deve poter cogliere.
  async function chiudiRiconsegna(id, { righe = null, note = null } = {}) {
    const res = await apiChiudiRiconsegna(id, { righe, note })
    emitDataChanged(TAB_ENTITIES.RESO, id)
    emitDataChanged(TAB_ENTITIES.ORDINE, null)
    return res.data.data
  }

  // Riapre una chiusura: round-trip esatto della precedente (l'ordine torna
  // PARZIALMENTE_EVASO, la quota torna ri-spedibile).
  async function riapriRiconsegna(id, { righe = null } = {}) {
    const res = await apiRiapriRiconsegna(id, { righe })
    emitDataChanged(TAB_ENTITIES.RESO, id)
    emitDataChanged(TAB_ENTITIES.ORDINE, null)
    return res.data.data
  }

  // --- Righe ---

  async function loadRighe(resoId) {
    const res = await listRighe(resoId)
    return res.data.data
  }

  async function addRiga(resoId, payload) {
    const res = await createRiga(resoId, payload)
    emitDataChanged(TAB_ENTITIES.RESO, resoId)
    return res.data.data
  }

  async function aggiornaRiga(resoId, rigaId, payload) {
    const res = await updateRiga(resoId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.RESO, resoId)
    return res.data.data
  }

  async function eliminaRiga(resoId, rigaId) {
    const res = await deleteRiga(resoId, rigaId)
    emitDataChanged(TAB_ENTITIES.RESO, resoId)
    return res.data.data
  }


  return {
    // state
    items, totalRecords, loading, hasSearched, filters,
    // testata
    fetchList, fetchDetail, create, update, elimina,
    // azioni di dominio
    conferma, annulla, generaRiconsegna, chiudiRiconsegna, riapriRiconsegna,
    // righe
    loadRighe, addRiga, aggiornaRiga, eliminaRiga,
  }
}, {
  userScoped: true,
})
