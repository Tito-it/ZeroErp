// Pinia store per la gestione pratiche (lista, dettaglio, creazione, azioni).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listPratiche, getPratica, createPratica, updatePratica,
  cambiaStatoPratica, assegnaPratica,
  sospendiPratica, riattivaPratica,
  fetchGiornale, fetchSospensioni,
  fetchCodaLavoro, prendiInCaricoFlusso, listFlussi, fetchPercorso,
} from '../api/pratiche-api'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'
import { useAuthStore } from '../../stores/auth'

export const usePraticheStore = defineStore('pratiche', () => {
  const { emitDataChanged } = useTabEvents()
  const auth = useAuthStore()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  // Default data_da: 1 gennaio anno corrente - 1
  const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

  const filters = ref({
    search: '',
    stato_id: null,
    priorita_id: null,
    risorsa_umana_id: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 10,
    offset: 0,
    order_by: 'data_insert',
    order_dir: 'desc'
  })

  // Scopo: Carica lista paginata pratiche con filtri.
  // Regola: la search testuale richiede minimo 3 caratteri.
  // Se la search viene svuotata e non ci sono filtri attivi, torna allo stato iniziale.
  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()
    const hasFilters = f.stato_id != null || f.priorita_id != null
      || f.risorsa_umana_id != null || f.data_a != null

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
    if (!searchTerm && !hasFilters && !hasSearched.value) {
      return
    }
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
      // Refactor operatore-emittenti: usa emittenteCorrente (1-a-1
      // dell'operatore), NON `auth.user.emittente.emittente_fiscale_id`
      // che per admin globale ritornerebbe il "gestore globale" via
      // cascata 4b di fn_get_user_profile — semantica diversa.
      const emittenteId = auth.emittenteCorrente?.id
      if (!emittenteId) {
        items.value = []
        totalRecords.value = 0
        return
      }
      params.emittente_fiscale_id = emittenteId
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.stato_id != null) params.stato_id = f.stato_id
      if (f.priorita_id != null) params.priorita_id = f.priorita_id
      if (f.risorsa_umana_id != null) params.risorsa_umana_id = f.risorsa_umana_id
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      const res = await listPratiche(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo pratica.
  async function fetchDetail(praticaId) {
    const res = await getPratica(praticaId)
    return res.data.data
  }

  // Scopo: Crea nuova pratica. emittente_fiscale_id viene dall'identita
  // 1-a-1 dell'operatore corrente (refactor operatore-emittenti); per
  // admin globali e' null e la creazione rimane bloccata lato backend.
  async function create(payload) {
    const emittenteId = auth.emittenteCorrente?.id
    const res = await createPratica({ ...payload, emittente_fiscale_id: emittenteId })
    emitDataChanged(TAB_ENTITIES.PRATICA, res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili della pratica.
  async function update(praticaId, payload) {
    const res = await updatePratica(praticaId, payload)
    emitDataChanged(TAB_ENTITIES.PRATICA, praticaId)
    return res.data.data
  }

  // Scopo: Cambia stato pratica (BOZZA→APERTA, APERTA→CHIUSA, ecc.).
  async function cambiaStato(praticaId, payload) {
    const res = await cambiaStatoPratica(praticaId, payload)
    emitDataChanged(TAB_ENTITIES.PRATICA, praticaId)
    return res.data.data
  }

  // Scopo: Assegna pratica a risorsa umana / unita' organizzativa.
  async function assegna(praticaId, payload) {
    const res = await assegnaPratica(praticaId, payload)
    emitDataChanged(TAB_ENTITIES.PRATICA, praticaId)
    return res.data.data
  }

  // Scopo: Sospendi pratica.
  async function sospendi(praticaId, payload = {}) {
    const res = await sospendiPratica(praticaId, payload)
    emitDataChanged(TAB_ENTITIES.PRATICA, praticaId)
    return res.data.data
  }

  // Scopo: Riattiva pratica sospesa.
  async function riattiva(praticaId, payload = {}) {
    const res = await riattivaPratica(praticaId, payload)
    emitDataChanged(TAB_ENTITIES.PRATICA, praticaId)
    return res.data.data
  }

  // Scopo: Carica giornale (audit log) della pratica.
  async function loadGiornale(praticaId) {
    const res = await fetchGiornale(praticaId)
    return res.data.data
  }

  // Scopo: Carica storico sospensioni della pratica.
  async function loadSospensioni(praticaId) {
    const res = await fetchSospensioni(praticaId)
    return res.data.data
  }

  // --- Coda lavoro operatore ---
  const codaLavoro = ref([])
  const codaLoading = ref(false)

  // Scopo: Carica coda lavoro dell'operatore corrente su tre livelli.
  // Usa emittenteCorrente (1-a-1) per coerenza col refactor.
  async function loadCodaLavoro() {
    const emittenteId = auth.emittenteCorrente?.id
    if (!emittenteId) { codaLavoro.value = []; return }
    codaLoading.value = true
    try {
      const res = await fetchCodaLavoro({ emittente_fiscale_id: emittenteId })
      codaLavoro.value = res.data.data.results
    } finally {
      codaLoading.value = false
    }
  }

  // Scopo: Prendi in carico un flusso DA_ESEGUIRE.
  async function prendiInCarico(flussoId) {
    const res = await prendiInCaricoFlusso(flussoId)
    emitDataChanged(TAB_ENTITIES.PRATICA)
    return res.data.data
  }

  // --- Flussi pratica ---

  // Scopo: Carica flussi di una pratica.
  async function loadFlussi(praticaId) {
    const res = await listFlussi(praticaId)
    return res.data.data.results
  }

  // Percorso suggerito (roadmap): template_flussi del tipo + stato istanziazione.
  async function loadPercorso(praticaId) {
    const res = await fetchPercorso(praticaId)
    return res.data.data.results
  }

  // --- Pratica selezionata nella dashboard ---
  const selectedPraticaId = ref(null)

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, create, update,
    cambiaStato, assegna, sospendi, riattiva,
    loadGiornale, loadSospensioni,
    codaLavoro, codaLoading, loadCodaLavoro,
    prendiInCarico, loadFlussi, loadPercorso,
    selectedPraticaId,
  }
})
