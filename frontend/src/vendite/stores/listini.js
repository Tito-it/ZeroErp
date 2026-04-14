// Store Pinia per la gestione listini vendite.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listListini, getListino, createListino, updateListino, listVersioni } from '../api/listini'
import { useTabEvents } from '../../core/composables/useTabEvents'

export const useListiniStore = defineStore('vendite-listini', () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  // Cache versioni per listino: { [listino_id]: [versione, ...] }.
  // Popolata dopo fetchList o on-expand riga; invalidata su create/update versione.
  const versioniByListino = ref({})

  const filters = ref({
    search: '',
    utility_id: null,
    tipologia_id: null,
    attivo: true,
    limit: 10,
    offset: 0,
    order_by: 'descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    if (searchTerm.length > 0 && searchTerm.length < 3) return

    loading.value = true
    try {
      const params = {}
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.utility_id != null) params.utility_id = f.utility_id
      if (f.tipologia_id != null) params.tipologia_id = f.tipologia_id
      if (f.attivo != null) params.attivo = f.attivo

      const res = await listListini(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
      // Preload versioni per i listini correnti (expansion default-aperta).
      // Esegue subito dopo l'aggiornamento di items, in parallelo. Eventuali
      // errori del singolo listino sono gia' gestiti da fetchVersioniListino.
      await preloadVersioniForCurrentItems()
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getListino(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createListino(payload)
    emitDataChanged('listino', res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateListino(id, payload)
    emitDataChanged('listino', id)
    return res.data.data
  }

  // Scopo: Carica le versioni di un listino e le mette in cache locale.
  //        Restituisce sempre la lista (anche cached). Errore: lista vuota.
  async function fetchVersioniListino(listinoId) {
    if (!listinoId) return []
    try {
      const res = await listVersioni(listinoId)
      const list = res.data.data.results || []
      versioniByListino.value = { ...versioniByListino.value, [listinoId]: list }
      return list
    } catch {
      versioniByListino.value = { ...versioniByListino.value, [listinoId]: [] }
      return []
    }
  }

  // Scopo: Pre-carica versioni per tutti i listini correntemente in lista
  //        e fa il prune delle entry obsolete (listini non piu' in lista).
  //        Usato in fetchList per supportare expansion default-aperta senza
  //        memory leak su uso prolungato.
  async function preloadVersioniForCurrentItems() {
    const ids = items.value.map(i => i.id)
    // Prune: tieni solo le entry dei listini correnti.
    const currentIds = new Set(ids)
    const pruned = {}
    for (const k of Object.keys(versioniByListino.value)) {
      if (currentIds.has(Number(k))) pruned[k] = versioniByListino.value[k]
    }
    versioniByListino.value = pruned

    if (ids.length === 0) return
    await Promise.all(ids.map(id => fetchVersioniListino(id)))
  }

  // Scopo: Invalida la cache versioni di un listino e (default) la ricarica.
  async function invalidateVersioniListino(listinoId, { reload = true } = {}) {
    if (!listinoId) return
    if (reload) {
      await fetchVersioniListino(listinoId)
    } else {
      const next = { ...versioniByListino.value }
      delete next[listinoId]
      versioniByListino.value = next
    }
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    versioniByListino,
    fetchList, fetchDetail, create, update,
    fetchVersioniListino, preloadVersioniForCurrentItems, invalidateVersioniListino
  }
})
