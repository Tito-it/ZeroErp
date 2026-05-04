// Store Pinia per la gestione preventivi vendita (lista, dettaglio, CRUD, azioni stato).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listPreventivi, getPreventivo, createPreventivo, updatePreventivo, deletePreventivo,
  cambiaStatoPreventivo, creaRevisione,
  listRighe, createRiga, updateRiga, deleteRiga, getRiepilogoIva,
  listIndirizzi, upsertIndirizzo,
  pushCommessa, statoFatturazione, generaPratica, listPratiche,
} from '../api/preventiviApi'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../../core/constants'

export const usePreventiviStore = defineStore('vendite-preventivi', () => {
  const { emitDataChanged } = useTabEvents()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

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
    solo_revisione_attiva: true,
    limit: 25,
    offset: 0,
    order_by: 'data',
    order_dir: 'desc'
  })

  // Scopo: Carica lista paginata preventivi con filtri.
  // Il backend usa page/page_size; il composable useSearchTable usa offset/limit.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    // data_da conta come filtro attivo (default anno-1 garantisce l'auto-load
    // della lista all'apertura, coerente con frontend-standards "Filtro data
    // standard"). Senza questo l'empty-state guard sotto bloccherebbe il
    // primo fetch e l'operatore vedrebbe la lista vuota.
    const hasFilters = f.stato != null || f.billing_account_id != null
      || f.utility_id != null || f.data_a != null || f.data_da != null

    // Search con meno di 3 caratteri e nessun filtro attivo → svuota i
    // risultati precedenti (coerenza UX: niente dati obsoleti visibili).
    if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }
    if (!searchTerm && !hasFilters && !hasSearched.value) return
    // Search svuotata senza filtri → torna a stato vuoto
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
      if (f.stato != null) params.stato = f.stato
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_al = f.data_a
      // Passa solo_revisione_attiva sempre esplicito: se l'operatore vuole
      // lo storico (toggle ON => filtro OFF) il BE deve riceverlo come 'false'.
      params.solo_revisione_attiva = f.solo_revisione_attiva ? 'true' : 'false'
      // Conversione offset/limit → page/page_size per il backend
      const pageSize = f.limit || 25
      const page = Math.floor((f.offset || 0) / pageSize) + 1
      params.page = page
      params.page_size = pageSize
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      const res = await listPreventivi(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

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

  // Scopo: Cambia stato preventivo (BOZZA→EMESSO, EMESSO→ACCETTATO, ecc.).
  // extras: payload aggiuntivo per transizioni che richiedono dati di processo.
  // Caso noto: EMESSO → ACCETTATO richiede fatturazione_immediata + competenza_mese
  // (vedi backend preventivi_service.cambia_stato gate accettazione).
  async function cambiaStato(id, nuovoStato, extras = {}) {
    const payload = { nuovo_stato: nuovoStato, ...extras }
    const res = await cambiaStatoPreventivo(id, payload)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
  }

  // Scopo: Crea nuova revisione del preventivo.
  async function nuovaRevisione(id) {
    const res = await creaRevisione(id)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, id)
    return res.data.data
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
    cambiaStato, nuovaRevisione,
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
