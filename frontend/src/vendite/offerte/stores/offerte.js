// Store Pinia per la gestione offerte commerciali (lista, dettaglio, CRUD,
// transizioni stato, revisioni, push contratto, eccezioni).
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items +
// filters dell'utente non devono persistere per l'eventuale utente successivo
// sullo stesso browser.
//
// Utility 1:1: gestita inline nel payload `create` / `update` testata
// (atomicita' BE via `OfferteService._add_utility_inline` /
// `_upsert_utility_inline`). Nessuna action dedicata nello store:
// l'esposizione separata (POST/PATCH `/utility/`) resta come endpoint BE
// per smoke test e consumer esterni, ma il drawer FE non la usa.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useTabEvents } from '../../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  annullaOfferta,
  createEccezione,
  createOfferta,
  creaRevisioneOfferta,
  deleteEccezione,
  deleteOfferta,
  emettiOfferta,
  getOfferta,
  listEccezioni,
  listOfferte,
  listRevisioniOfferta,
  pushOffertaAContratto,
  registraEsitoOfferta,
  updateEccezione,
  updateOfferta,
} from '../api/offerteApi'

export const useOfferteStore = defineStore('vendite-offerte', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  // Default data_da: 1 gennaio anno corrente - 1. Coerente con frontend-standards
  // "Filtro data standard" — la lista parte popolata sull'ultimo anno+anno corrente.
  const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

  const filters = ref({
    search: '',
    stato_codice_interno: null,
    billing_account_id: null,
    utility_id: null,
    listino_id: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    // Default coerente con `OfferteSearchTable.useSearchTable.defaultSortField`:
    // entrambi devono puntare a una colonna visibile e sortable, altrimenti
    // PrimeVue genera un sort-indicator "fantasma" (underline anomala
    // sotto le label) sulla riga header. Allineare se si cambia uno dei due.
    // Default `validita_dal desc`: offerte con inizio validita' piu' recente
    // in cima (allineato al pattern preventivi/contratti).
    order_by: 'validita_dal',
    order_dir: 'desc',
  })

  // Scopo: Carica lista paginata offerte con filtri standard. Empty-state
  //        guard: senza filtri attivi e senza search non si chiama il BE.
  //        `data_da` default-anno-1 conta come filtro: la lista si popola al mount.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.stato_codice_interno != null
      || f.billing_account_id != null
      || f.utility_id != null
      || f.listino_id != null
      || f.data_a != null
      || f.data_da != null

    if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }
    if (!searchTerm && !hasFilters && !hasSearched.value) return
    if (!searchTerm && !hasFilters) {
      items.value = []
      totalRecords.value = 0
      hasSearched.value = false
      return
    }

    loading.value = true
    try {
      const params = {}
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.stato_codice_interno != null) params.stato_codice_interno = f.stato_codice_interno
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.listino_id != null) params.listino_id = f.listino_id
      // I filtri data BE si chiamano validita_dal_min / validita_dal_max
      // (vedi views_offerte.py): si applicano sul `validita_dal` della testata.
      if (f.data_da) params.validita_dal_min = f.data_da
      if (f.data_a) params.validita_dal_max = f.data_a
      params.limit = f.limit || 25
      params.offset = f.offset || 0
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      const res = await listOfferte(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo offerta (testata + eccezioni + utility 1:1).
  async function fetchDetail(id) {
    const res = await getOfferta(id)
    return res.data.data
  }

  // Scopo: Crea nuova offerta BOZZA. Il codice OFC-* arriva dal trigger DB.
  async function create(payload) {
    const res = await createOfferta(payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna testata offerta (solo se in BOZZA).
  async function update(id, payload) {
    const res = await updateOfferta(id, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // Scopo: Hard-delete offerta BOZZA orfana (flusso abbandono drawer create).
  async function elimina(id) {
    const res = await deleteOfferta(id)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // --- Transizioni stato ---

  // BOZZA -> EMESSA. Genera+persiste documento + allegati (multipart) lato
  // BE in transazione atomica. `allegati` = array di File (opzionale).
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiOfferta(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // EMESSA -> ACCETTATA / RIFIUTATA. Motivazione obbligatoria su RIFIUTATA.
  async function registraEsito(id, { esito, motivazione }) {
    const res = await registraEsitoOfferta(id, { esito, motivazione })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // BOZZA -> ANNULLATA. Motivazione obbligatoria.
  async function annulla(id, { motivazione }) {
    const res = await annullaOfferta(id, { motivazione })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    return res.data.data
  }

  // EMESSA -> rev.N+1 (BOZZA). La fn DB marca la rev.N corrente come SUPERATA.
  async function creaRevisione(id) {
    const res = await creaRevisioneOfferta(id)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    // Emette anche per la nuova rev (la lista deve aggiornare entrambe).
    if (res.data.data?.id != null) {
      emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, res.data.data.id)
    }
    return res.data.data
  }

  // Catena revisioni (lettura libera).
  async function loadRevisioni(id) {
    const res = await listRevisioniOfferta(id)
    return res.data.data
  }

  // ACCETTATA -> contratto DRAFT (idempotente). Ritorna
  // { contratto_id, contratto_codice, sorgente_uid }.
  async function pushAContratto(id, { praticaId = null } = {}) {
    const res = await pushOffertaAContratto(id, { praticaId })
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, id)
    // Emette anche per il contratto generato (apre/refresh tab contratti).
    if (res.data.data?.contratto_id != null) {
      emitDataChanged(TAB_ENTITIES.CONTRATTO, res.data.data.contratto_id)
    }
    return res.data.data
  }

  // --- Eccezioni ---

  async function loadEccezioni(offertaId) {
    const res = await listEccezioni(offertaId)
    return res.data.data
  }

  async function addEccezione(offertaId, payload) {
    const res = await createEccezione(offertaId, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  async function aggiornaEccezione(offertaId, eccezioneId, payload) {
    const res = await updateEccezione(offertaId, eccezioneId, payload)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  async function eliminaEccezione(offertaId, eccezioneId) {
    const res = await deleteEccezione(offertaId, eccezioneId)
    emitDataChanged(TAB_ENTITIES.OFFERTA_COMMERCIALE, offertaId)
    return res.data.data
  }

  return {
    // state
    items, totalRecords, loading, hasSearched, filters,
    // testata (utility 1:1 atomica via payload.utility inline)
    fetchList, fetchDetail, create, update, elimina,
    // transizioni
    emetti, registraEsito, annulla, creaRevisione, loadRevisioni, pushAContratto,
    // eccezioni
    loadEccezioni, addEccezione, aggiornaEccezione, eliminaEccezione,
  }
}, {
  userScoped: true,
})
