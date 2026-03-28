// Pinia store per la gestione pratiche (lista, dettaglio, creazione, azioni).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listPratiche, getPratica, createPratica, updatePratica,
  cambiaStatoPratica, assegnaPratica,
  sospendiPratica, riattivaPratica,
  fetchGiornale, fetchSospensioni
} from '../api/pratiche-api'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { useAuthStore } from '../../stores/auth'

export const usePraticheStore = defineStore('pratiche', () => {
  const { emitDataChanged } = useTabEvents()
  const auth = useAuthStore()
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)

  const filters = ref({
    search: '',
    stato_id: null,
    priorita_id: null,
    risorsa_umana_id: null,
    limit: 25,
    offset: 0,
    order_by: 'date_insert',
    order_dir: 'desc'
  })

  // Scopo: Carica lista paginata pratiche con filtri.
  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const emittenteId = auth.user?.emittente?.id
      if (emittenteId) params.emittente_fiscale_id = emittenteId
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.stato_id != null) params.stato_id = f.stato_id
      if (f.priorita_id != null) params.priorita_id = f.priorita_id
      if (f.risorsa_umana_id != null) params.risorsa_umana_id = f.risorsa_umana_id
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      const res = await listPratiche(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio completo pratica.
  async function fetchDetail(praticaId) {
    const res = await getPratica(praticaId)
    return res.data.data
  }

  // Scopo: Crea nuova pratica (aggiunge emittente_fiscale_id dal profilo utente).
  async function create(payload) {
    const emittenteId = auth.user?.emittente?.id
    const res = await createPratica({ ...payload, emittente_fiscale_id: emittenteId })
    emitDataChanged('pratica', res.data.data.id)
    return res.data.data
  }

  // Scopo: Aggiorna campi editabili della pratica.
  async function update(praticaId, payload) {
    const res = await updatePratica(praticaId, payload)
    emitDataChanged('pratica', praticaId)
    return res.data.data
  }

  // Scopo: Cambia stato pratica (BOZZA→APERTA, APERTA→CHIUSA, ecc.).
  async function cambiaStato(praticaId, payload) {
    const res = await cambiaStatoPratica(praticaId, payload)
    emitDataChanged('pratica', praticaId)
    return res.data.data
  }

  // Scopo: Assegna pratica a risorsa umana / unita' organizzativa.
  async function assegna(praticaId, payload) {
    const res = await assegnaPratica(praticaId, payload)
    emitDataChanged('pratica', praticaId)
    return res.data.data
  }

  // Scopo: Sospendi pratica.
  async function sospendi(praticaId, payload = {}) {
    const res = await sospendiPratica(praticaId, payload)
    emitDataChanged('pratica', praticaId)
    return res.data.data
  }

  // Scopo: Riattiva pratica sospesa.
  async function riattiva(praticaId, payload = {}) {
    const res = await riattivaPratica(praticaId, payload)
    emitDataChanged('pratica', praticaId)
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

  return {
    items, totalRecords, loading, filters,
    fetchList, fetchDetail, create, update,
    cambiaStato, assegna, sospendi, riattiva,
    loadGiornale, loadSospensioni
  }
})
