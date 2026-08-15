// Store Pinia per la gestione listini vendite.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listListini, getListino, createListino, updateListino, listVersioni } from '../api/listini'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useListiniStore = defineStore('vendite-listini', () => {
  const { emitDataChanged } = useTabEvents()


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
    // `codice`: e' il preset default del seed della lista `vendite.listini`
    // (identificatore, colonna fissata). Il `defaultSortField` del componente
    // e' dormiente finche' questo preset esiste: la verita' e' qui.
    order_by: 'codice',
    order_dir: 'asc'
  })

  // Lista via BB condiviso (migrazione 2026-08-10): guardia di versione anti-race
  // + guardia della ricerca corta, che qui era scritta a mano.
  const { items, totalRecords, loading, hasSearched, fetchList: fetchListBase } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    ricercaCorta: 'svuota',
    buildParams: (f, searchTerm) => {
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
      return params
    },
    fetchPage: listListini,
  })

  // Preload versioni per i listini correnti (expansion default-aperta): resta
  // FUORI dal BB perche' e' un secondo giro di fetch del dominio, non parte del
  // ciclo di lista. ⚠️ Differenza dichiarata rispetto a prima: girava dentro la
  // finestra di `loading`, ora subito dopo — lo spinner della lista si spegne un
  // istante prima che le versioni siano in casa. Gli errori del singolo listino
  // li gestisce gia' `fetchVersioniListino`.
  // Il preload parte SOLO se la fetch ha davvero aggiornato `items`: una
  // guardia (ricerca corta) o una risposta scartata dal guard di versione non
  // devono potare la cache versioni a vuoto ne' rilanciare il preload sugli
  // id di un'altra chiamata (doppioni di N richieste versioni).
  async function fetchList() {
    const landed = await fetchListBase()
    if (landed) await preloadVersioniForCurrentItems()
  }

  async function fetchDetail(id) {
    const res = await getListino(id)
    return res.data.data
  }

  async function create(payload) {
    const res = await createListino(payload)
    emitDataChanged(TAB_ENTITIES.LISTINO, res.data.data.id)
    return res.data.data
  }

  async function update(id, payload) {
    const res = await updateListino(id, payload)
    emitDataChanged(TAB_ENTITIES.LISTINO, id)
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
}, {
  // Reset automatico al logout (autoResetPlugin): items + cache versioniByListino
  // dell'utente non devono persistere per l'eventuale utente successivo.
  userScoped: true,
})
