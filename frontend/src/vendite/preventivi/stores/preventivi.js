// Store Pinia per la gestione preventivi vendita (lista, dettaglio, CRUD, azioni stato).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listPreventivi, getPreventivo, createPreventivo, updatePreventivo, deletePreventivo,
  cambiaStatoPreventivo, emettiPreventivo, creaRevisione, listRevisioni,
  listRighe, createRiga, updateRiga, deleteRiga, getRiepilogoIva,
  listIndirizzi, upsertIndirizzo,
  pushCommessa, statoFatturazione, generaPratica, listPratiche,
} from '../api/preventiviApi'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useListaEmptyStateFetch } from '../../../core/composables/useListaEmptyStateFetch'
import { TAB_ENTITIES } from '../../../core/constants'

export const usePreventiviStore = defineStore('vendite-preventivi', () => {
  const { emitDataChanged } = useTabEvents()

  // Default data_da: 1 gennaio anno corrente - 1
  const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

  const filters = ref({
    search: '',
    stato: null,
    billing_account_id: null,
    utility_id: null,
    data_da: defaultDataDa,
    data_a: null,
    // Default true: la lista mostra solo l'ultima revisione per numero
    // (le revisioni superseded restano nello storico DB ma non in UI).
    // Toggle "Mostra storico revisioni" lo flippa.
    solo_attiva: true,
    limit: 25,
    offset: 0,
    order_by: 'data',
    order_dir: 'desc'
  })

  // Lista paginata preventivi con guardia empty-state standard (BB
  // useListaEmptyStateFetch). `data_da` default-anno-1 conta come filtro attivo:
  // garantisce l'auto-load all'apertura (frontend-standards "Filtro data standard").
  // Paginazione limit/offset standard (riallineata 2026-06-03: il BE usa ora
  // parse_list_params, era l'unico dominio su page/page_size).
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    hasActiveFilters: (f) => f.stato != null || f.billing_account_id != null
      || f.utility_id != null || f.data_a != null || f.data_da != null,
    buildParams: (f, searchTerm) => {
      const params = {}
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.stato != null) params.stato = f.stato
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_al = f.data_a
      // Passa solo_attiva sempre esplicito: se l'operatore vuole lo storico
      // (toggle ON => filtro OFF) il BE deve riceverlo come 'false'.
      params.solo_attiva = f.solo_attiva ? 'true' : 'false'
      // Paginazione standard limit/offset (allineata a offerte/ordini/clienti;
      // la view BE ora usa parse_list_params, 2026-06-03).
      params.limit = f.limit || 25
      params.offset = f.offset || 0
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      return params
    },
    fetchPage: listPreventivi,
  })

  // Scopo: Dettaglio completo preventivo.
  async function fetchDetail(id) {
    const res = await getPreventivo(id)
    return res.data.data
  }

  // Scopo: Crea nuovo preventivo.
  async function create(payload) {
    const res = await createPreventivo(payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili del preventivo.
  async function update(id, payload) {
    const res = await updatePreventivo(id, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Hard-delete preventivo BOZZA orfano (flusso abbandono bozza drawer).
  async function elimina(id) {
    const res = await deletePreventivo(id)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Cambia stato preventivo (EMESSO→ACCETTATO, *→ANNULLATO, ecc.).
  // extras: payload aggiuntivo per transizioni che richiedono dati di processo.
  // Caso noto: EMESSO → ACCETTATO richiede fatturazione_immediata + competenza_mese
  // (vedi backend preventivi_service.cambia_stato gate accettazione).
  // NB refactor 2026-05-28: BOZZA->EMESSO NON passa piu' da qui — usare
  // `emetti()` sotto (orchestra atomic state + documento + allegati via
  // PreventivoEmissioneDialog). Il BE rifiuterebbe E_PREV_VALIDAZIONE.
  async function cambiaStato(id, nuovoStato, extras = {}) {
    const payload = { nuovo_stato: nuovoStato, ...extras }
    const res = await cambiaStatoPreventivo(id, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: BOZZA -> EMESSO (multipart). Cambia stato + genera documento +
  // allegati in transazione atomica lato BE. Mirror del flusso offerta.
  // Invocata dal PreventivoEmissioneDialog (PreventiviDrawer intercetta
  // l'action 'emetti' e apre il dialog invece di chiamare cambiaStato).
  async function emetti(id, { allegati = [], templateId = null } = {}) {
    const res = await emettiPreventivo(id, { allegati, templateId })
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Crea nuova revisione del preventivo.
  async function nuovaRevisione(id) {
    const res = await creaRevisione(id)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Lista catena revisioni del preventivo (stesso `numero`, ordinate
  // per `rev` ASC). Mirror del pattern offerte.
  async function loadRevisioni(id) {
    const res = await listRevisioni(id)
    return res.data?.data ?? []
  }

  // --- Righe ---

  // Scopo: Carica righe del preventivo.
  async function loadRighe(preventivoId) {
    const res = await listRighe(preventivoId)
    return res.data.data
  }

  // Scopo: Aggiunge riga al preventivo.
  async function addRiga(preventivoId, payload) {
    const res = await createRiga(preventivoId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Aggiorna riga preventivo.
  async function aggiornaRiga(preventivoId, rigaId, payload) {
    const res = await updateRiga(preventivoId, rigaId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Elimina riga preventivo (soft delete).
  async function eliminaRiga(preventivoId, rigaId) {
    const res = await deleteRiga(preventivoId, rigaId)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Carica riepilogo IVA aggregato del preventivo (regola fiscale
  //        DPR 633/72 art. 21). Una entry per aliquota IVA distinta. Il
  //        ricalcolo e' atomico lato DB su ogni mutazione delle righe.
  async function loadRiepilogoIva(preventivoId) {
    const res = await getRiepilogoIva(preventivoId)
    return res.data.data
  }

  // --- Indirizzi ---

  // Scopo: Carica indirizzi del preventivo.
  async function loadIndirizzi(preventivoId) {
    const res = await listIndirizzi(preventivoId)
    return res.data.data
  }

  // Scopo: Upsert indirizzo preventivo.
  async function salvaIndirizzo(preventivoId, payload) {
    const res = await upsertIndirizzo(preventivoId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // --- Integrazione ---

  // Scopo: Push preventivo in commessa per fatturazione.
  async function inviaACommessa(preventivoId) {
    const res = await pushCommessa(preventivoId)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Carica stato fatturazione del preventivo.
  async function loadStatoFatturazione(preventivoId) {
    const res = await statoFatturazione(preventivoId)
    return res.data.data
  }

  // Scopo: Genera pratica esecutiva da preventivo.
  async function creaPratica(preventivoId, payload) {
    const res = await generaPratica(preventivoId, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, preventivoId)
    return res.data.data
  }

  // Scopo: Carica pratiche collegate al preventivo.
  async function loadPratiche(preventivoId) {
    const res = await listPratiche(preventivoId)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update, elimina,
    cambiaStato, emetti, nuovaRevisione, loadRevisioni,
    loadRighe, addRiga, aggiornaRiga, eliminaRiga, loadRiepilogoIva,
    loadIndirizzi, salvaIndirizzo,
    inviaACommessa, loadStatoFatturazione,
    creaPratica, loadPratiche,
  }
}, {
  // Reset automatico al logout (autoResetPlugin): items + filters dell'utente
  // non devono persistere per l'eventuale utente successivo sullo stesso browser.
  userScoped: true,
})
