// Pinia store per la gestione operatori (lista, dettaglio, CRUD, override).
// I lookup (UO, qualifiche, aree, azioni, emittenti) sono stati spostati
// nei componenti via useLookup — lo store gestisce solo dati operatori.
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    una copia a mano del suo `buildParams` su `useListaEmptyStateFetch`, con
//    un ripiego del verso scritto `'ASC'` maiuscolo — l'unico nel frontend.
//    Non passa da una factory perche' lo store e' quasi tutto stato di
//    dominio (dettaglio corrente, override, scope emittenti): la lista e' una
//    parte, e la sua casa e' il core.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import {
  listOperatori,
  getOperatore,
  createOperatore,
  updateOperatore,
  disabilitaOperatore,
  getOverrideAree,
  putOverrideAree,
  getOverrideAzioni,
  putOverrideAzioni,
  getOverrideOggetti,
  putOverrideOggetti,
  getEmittentiScope,
  putEmittentiScope,
  getPermessiEreditati,
  getPermessiEffettivi,
  getPermessiRiepilogo,
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const { emitDataChanged } = useTabEvents()

export const useOperatoriStore = defineStore('amm-operatori', () => {
  // Dettaglio/corrente
  const currentOperatore = ref(null)
  const loadingDetail = ref(false)

  // Lista (filtri sincronizzati con la toolbar). Multi-face auth (Fase 7):
  // solo is_super_admin + is_active + unita_organizzativa_id. Il legacy
  // ruolo_sistema e' rimosso. Parte piena: e' l'anagrafica degli operatori.
  // `includi_di_prova`: gli utenti del provisioning di sviluppo restano fuori
  // finche' non li si chiede (il backend li nasconde quando il parametro
  // manca: R-4 del brief-db-processi-accensione-per-ambiente).
  const lista = useListaStoreCore({
    fetchPage: listOperatori,
    startsEmpty: false,
    filterDefaults: {
      is_super_admin: null,
      unita_organizzativa_id: null,
      is_active: null,
      includi_di_prova: null,
    },
    orderBy: 'soggetto_cognome',
  })

  // Override corrente
  const overrideAree = ref([])
  const overrideAzioni = ref([])
  const overrideOggetti = ref([])
  // Livelli ereditati dal profilo (sola lettura). Le due liste vuote sono lo
  // stato iniziale E la risposta legittima di un utente senza profili: il
  // pannello le legge come «default», non come «non ancora caricato».
  const permessiEreditati = ref({ aree: [], azioni: [] })
  // Permessi EFFETTIVI su azioni e oggetti, col tetto d'area (sola lettura).
  // Cambiano a ogni salvataggio di un override (l'ereditato no): i `save*`
  // qui sotto li ricaricano.
  const permessiEffettivi = ref({ azioni: [], oggetti: [] })
  // Il riepilogo PER AREA dell'operatore corrente (livello, override scritti,
  // voci limitate): il badge «override» dell'elenco aree del pannello. Stessa
  // sede della lista operatori (`fn_get_permessi_riepilogo_aree`).
  const riepilogoAree = ref([])
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

  // --- Override aree ---
  async function fetchOverrideAree(authUserId) {
    const res = await getOverrideAree(authUserId)
    overrideAree.value = res.data.data.results
  }

  async function saveOverrideAree(authUserId, items) {
    const res = await putOverrideAree(authUserId, items)
    overrideAree.value = res.data.data.results
    await Promise.all([fetchPermessiEffettivi(authUserId), fetchRiepilogoAree(authUserId)])
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
    await Promise.all([fetchPermessiEffettivi(authUserId), fetchRiepilogoAree(authUserId)])
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
    await Promise.all([fetchPermessiEffettivi(authUserId), fetchRiepilogoAree(authUserId)])
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

  // --- Permessi effettivi col tetto d'area (sola lettura) ---
  async function fetchPermessiEffettivi(authUserId) {
    const res = await getPermessiEffettivi(authUserId)
    permessiEffettivi.value = res.data.data
  }

  // --- Riepilogo per area dell'operatore corrente (sola lettura) ---
  async function fetchRiepilogoAree(authUserId) {
    const res = await getPermessiRiepilogo([authUserId])
    riepilogoAree.value = res.data.data.results
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
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,

    // Dettaglio
    currentOperatore,
    loadingDetail,
    fetchDetail,

    // CRUD
    create,
    update,
    disabilita,

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
    permessiEffettivi,
    fetchPermessiEffettivi,
    riepilogoAree,
    fetchRiepilogoAree,
    fetchEmittentiScope,
    saveEmittentiScope
  }
}, { userScoped: true })
