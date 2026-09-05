// Pinia store per la gestione operatori (lista, dettaglio, CRUD, override).
// I lookup (UO, qualifiche, aree, azioni, emittenti) sono stati spostati
// nei componenti via useLookup — lo store gestisce solo dati operatori.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import {
  listOperatori,
  getOperatore,
  createOperatore,
  updateOperatore,
  disabilitaOperatore,
  riattivaOperatore,
  getOverrideAree,
  putOverrideAree,
  getOverrideAzioni,
  putOverrideAzioni,
  getOverrideOggetti,
  putOverrideOggetti,
  getEmittentiScope,
  putEmittentiScope,
  getPermessiEreditati,
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const { emitDataChanged } = useTabEvents()

export const useOperatoriStore = defineStore('amm-operatori', () => {
  // Lista

  // Dettaglio/corrente
  const currentOperatore = ref(null)
  const loadingDetail = ref(false)

  // Filtri attivi (sincronizzati con la toolbar).
  // Multi-face auth (Fase 7): solo is_super_admin + is_active +
  // unita_organizzativa_id. Il legacy ruolo_sistema e' rimosso.
  const filters = ref({
    search: '',
    is_super_admin: null,
    unita_organizzativa_id: null,
    is_active: null,
    limit: 25,
    offset: 0,
    order_by: 'soggetto_cognome',
    order_dir: 'asc'
  })

  // Override corrente
  const overrideAree = ref([])
  const overrideAzioni = ref([])
  const overrideOggetti = ref([])
  // Livelli ereditati dal profilo (sola lettura). Le due liste vuote sono lo
  // stato iniziale E la risposta legittima di un utente senza profili: il
  // pannello le legge come «default», non come «non ancora caricato».
  const permessiEreditati = ref({ aree: [], azioni: [] })
  // Fase 2 multi-face: shape dichiarativo da fn DB
  // `script.fn_get_user_emittenti_scope`. Sostituisce la vecchia lista grezza.
  const emittentiScope = ref({
    scope_mode: 'GLOBAL',
    emittenti_ids: [],
    emittente_descrizione: null,
    allowed_scope_modes: ['GLOBAL', 'SINGLE'],
    can_change_scope: true,
    change_scope_reason: null,
  })

  // Lista via BB condiviso (migrazione 2026-08-10): la guardia di versione
  // anti-race che qui mancava. `alwaysFetch` conserva il comportamento: questa
  // lista si e' sempre caricata anche senza filtri.
  const { items, totalRecords, loading, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f, searchTerm) => {
      const params = {}
      if (f.search) params.search = f.search
      if (f.is_super_admin != null) params.is_super_admin = f.is_super_admin
      if (f.unita_organizzativa_id != null) params.unita_organizzativa_id = f.unita_organizzativa_id
      if (f.is_active != null) params.is_active = f.is_active
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'ASC'
      }
      return params
    },
    fetchPage: listOperatori,
  })

  async function fetchDetail(authUserId) {
    loadingDetail.value = true
    try {
      const res = await getOperatore(authUserId)
      currentOperatore.value = res.data.data
    } finally {
      loadingDetail.value = false
    }
  }

  async function create(payload) {
    const res = await createOperatore(payload)
    const created = res.data.data
    emitDataChanged(TAB_ENTITIES.OPERATORE, created.auth_user_id)
    return created
  }

  async function update(authUserId, payload) {
    const res = await updateOperatore(authUserId, payload)
    currentOperatore.value = res.data.data
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
    return res.data.data
  }

  async function disabilita(authUserId) {
    const res = await disabilitaOperatore(authUserId)
    currentOperatore.value = res.data.data
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
    return res.data.data
  }

  async function riattiva(authUserId) {
    const res = await riattivaOperatore(authUserId)
    currentOperatore.value = res.data.data
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
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
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
  }

  // --- Override azioni ---
  async function fetchOverrideAzioni(authUserId) {
    const res = await getOverrideAzioni(authUserId)
    overrideAzioni.value = res.data.data.results
  }

  async function saveOverrideAzioni(authUserId, items) {
    const res = await putOverrideAzioni(authUserId, items)
    overrideAzioni.value = res.data.data.results
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
  }

  // --- Override oggetti (v2 permessi) ---
  async function fetchOverrideOggetti(authUserId) {
    const res = await getOverrideOggetti(authUserId)
    overrideOggetti.value = res.data.data.results
  }

  async function saveOverrideOggetti(authUserId, items) {
    const res = await putOverrideOggetti(authUserId, items)
    overrideOggetti.value = res.data.data.results
    emitDataChanged(TAB_ENTITIES.OPERATORE, authUserId)
  }

  // --- Livelli ereditati dal profilo (sola lettura) ---
  // Serve al pannello permessi per mostrare cosa l'operatore ha GIA' senza
  // override. ⚠️ Liste vuote = nessun profilo copre la voce ⇒ default
  // (BLOCCATO / azione negata): e' un dato, non un caricamento mancato.
  async function fetchPermessiEreditati(authUserId) {
    const res = await getPermessiEreditati(authUserId)
    permessiEreditati.value = res.data.data
  }

  // --- Emittenti scope (Fase 2 multi-face: scope dichiarativo) ---
  async function fetchEmittentiScope(authUserId) {
    const res = await getEmittentiScope(authUserId)
    emittentiScope.value = res.data.data
  }

  // payload: { scope_mode: 'GLOBAL'|'SINGLE', emittenti_ids?: number[] }
  async function saveEmittentiScope(authUserId, payload) {
    const res = await putEmittentiScope(authUserId, payload)
    emittentiScope.value = res.data.data
    return res.data.data
  }

  return {
    // Lista
    items,
    totalRecords,
    loading,
    filters,
    fetchList,

    // Dettaglio
    currentOperatore,
    loadingDetail,
    fetchDetail,

    // CRUD
    create,
    update,
    disabilita,
    riattiva,

    // Override
    overrideAree,
    overrideAzioni,
    overrideOggetti,
    emittentiScope,
    fetchOverrideAree,
    saveOverrideAree,
    fetchOverrideAzioni,
    saveOverrideAzioni,
    fetchOverrideOggetti,
    saveOverrideOggetti,
    permessiEreditati,
    fetchPermessiEreditati,
    fetchEmittentiScope,
    saveEmittentiScope
  }
}, { userScoped: true })
