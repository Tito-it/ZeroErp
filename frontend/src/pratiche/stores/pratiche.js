// Pinia store per la gestione pratiche (lista, dettaglio, creazione, azioni).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
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

  // Default data_da: primo giorno del mese precedente. Le pratiche sono una
  // coda di lavoro: l'orizzonte operativo e' recente, il pregresso si
  // raggiunge allargando il DatePicker in toolbar (filtro sempre visibile).
  const _dataDa = new Date()
  _dataDa.setDate(1)
  _dataDa.setMonth(_dataDa.getMonth() - 1)
  const defaultDataDa = `${_dataDa.getFullYear()}-${String(_dataDa.getMonth() + 1).padStart(2, '0')}-01`

  const filters = ref({
    search: '',
    // Codice stato (es. 'APERTA'): il BE filtra per codice_interno via param
    // `stato` (fix 2026-06-12: prima si inviava `stato_id`, ignorato dal BE).
    stato: null,
    priorita_id: null,
    // Filtro tipo prestazione (home launcher: le tile "Comincia" atterrano
    // sulla dashboard con questo filtro preimpostato via query param).
    tipo_prestazione_id: null,
    risorsa_umana_id: null,
    // Lente di contesto canonica (D1, workflow v2): solo pratiche interne
    // (senza soggetto). Esclusiva con le lenti ruolo/istanza (usate dalle
    // viste embedded, non dalla dashboard).
    solo_interne: false,
    data_da: defaultDataDa,
    data_a: null,
    limit: 10,
    offset: 0,
    order_by: 'data_apertura',
    order_dir: 'desc'
  })

  // Scopo: Carica lista paginata pratiche con filtri.
  // Lista eager col filtro data SEMPRE attivo (data_da default = inizio mese
  // precedente): carica sempre, senza richiedere una ricerca. La search
  // testuale si applica solo da 3 caratteri; con 1-2 caratteri non rifetcha
  // (i risultati correnti restano, niente flicker durante la digitazione).
  // Lista via BB condiviso (migrazione 2026-08-10): guardia di versione anti-race
  // + guardia della ricerca corta, che qui era scritta a mano.
  // `alwaysFetch`: la lista si e' sempre caricata (con l'emittente corrente).
  // `ricercaCorta: 'ignora'`: qui la ricerca corta e' sempre stata un no-op
  // (la lista resta com'e', vedi sopra). Svuotare avrebbe anche effetti a
  // cascata sulla dashboard: `selectedItem` si risolve da `items`, e una lista
  // svuotata mentre si digita annulla il guard readonly della pratica
  // terminale selezionata e il contesto cliente del percorso.
  const { items, totalRecords, loading, hasSearched, fetchList: fetchListBase, svuota } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    ricercaCorta: 'ignora',
    buildParams: (f, searchTerm) => {
      const params = {}
      // Refactor operatore-emittenti: usa emittenteCorrente (1-a-1
      // dell'operatore), NON `auth.user.emittente.emittente_fiscale_id`
      // che per admin globale ritornerebbe il "gestore globale" via
      // cascata 4b di fn_get_user_profile — semantica diversa.
      params.emittente_fiscale_id = auth.emittenteCorrente?.id
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.stato) params.stato = f.stato
      if (f.priorita_id != null) params.priorita_id = f.priorita_id
      if (f.tipo_prestazione_id != null) params.tipo_prestazione_id = f.tipo_prestazione_id
      if (f.risorsa_umana_id != null) params.risorsa_umana_id = f.risorsa_umana_id
      if (f.solo_interne) params.solo_interne = true
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      return params
    },
    fetchPage: listPratiche,
  })

  // Senza emittente corrente non c'e' perimetro: lista vuota, nessuna chiamata.
  // E' stato del chiamante, non un filtro — resta fuori dal BB.
  async function fetchList() {
    if (!auth.emittenteCorrente?.id) {
      // `svuota` del BB, non un clear a mano: invalida anche le fetch in volo
      // (una risposta partita con l'emittente ancora impostato non deve
      // ripopolare la lista appena azzerata).
      svuota()
      return
    }
    await fetchListBase()
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
  // Dedup in-flight: home e dashboard la chiamano entrambe all'attivazione
  // (KeepAlive) — se una fetch e' gia' in corso la seconda non riparte.
  async function loadCodaLavoro() {
    if (codaLoading.value) return
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
