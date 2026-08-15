// Store Pinia per la gestione righe prezzo di una versione listino.
// Gestisce paginazione server-side, filtri (search articolo, billing_account)
// e reload post-operazione (create/delete riga, variazione %).
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listRighe } from '../api/listini'

export const useListiniRigheStore = defineStore('vendite-listini-righe', () => {
  // items / totalRecords / loading / hasSearched arrivano dal BB piu' sotto.
  // `hasSearched`: true dopo il primo fetch riuscito nel contesto corrente —
  // serve al refetch condizionale di onConfigLoaded (<ListaConfigurabile>) e
  // agli empty-state onesti.

  // Contesto corrente: listino e versione. Impostati dal drawer padre.
  const listinoId = ref(null)
  const versioneId = ref(null)

  const filters = ref({
    search: '',
    billing_account_id: null,
    // Default 10 righe/pagina coerente col pattern master-detail inline
    // (frontend-standards: 10 righe + rows-per-page-options [10, 25]).
    limit: 10,
    offset: 0,
    order_by: 'articolo_descrizione',
    order_dir: 'asc'
  })

  // Scopo: Carica la pagina corrente di righe dal backend con filtri attivi.
  // Lista via BB condiviso (migrazione 2026-08-10): guardia di versione anti-race
  // + guardia della ricerca corta. La precondizione su listino/versione resta un
  // wrapper: e' contesto del chiamante, non un filtro della lista.
  // `ricercaCorta: 'ignora'`: la ricerca corta qui e' sempre stata un no-op
  // (la lista resta com'e' mentre si digita, nessuna richiesta).
  // La destructure sta PRIMA di setContext/clearContext che usano `svuota`:
  // un domani un reset eager nel setup (watch immediate, initializer)
  // incontrerebbe la TDZ del `const`.
  const { items, totalRecords, loading, hasSearched, fetchList: fetchListBase, svuota } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    ricercaCorta: 'ignora',
    buildParams: (f, searchTerm) => {
      const params = {
        limit: f.limit,
        offset: f.offset,
      }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
      return params
    },
    fetchPage: (params) => listRighe(listinoId.value, versioneId.value, params),
  })

  // Scopo: Imposta il contesto listino/versione e resetta filtri e dati.
  // `svuota` del BB, non un clear a mano: invalida anche le fetch in volo (una
  // risposta della versione precedente non deve ripopolare la lista azzerata).
  function setContext(newListinoId, newVersioneId) {
    listinoId.value = newListinoId
    versioneId.value = newVersioneId
    svuota()
    filters.value.search = ''
    filters.value.billing_account_id = null
    filters.value.offset = 0
  }

  // Scopo: Svuota dati e contesto alla chiusura del drawer.
  function clearContext() {
    listinoId.value = null
    versioneId.value = null
    svuota()
  }

  async function fetchList() {
    if (!listinoId.value || !versioneId.value) return
    await fetchListBase()
  }

  return {
    items, totalRecords, loading, hasSearched,
    listinoId, versioneId,
    filters,
    setContext, clearContext, fetchList
  }
}, {
  // Reset automatico al logout (autoResetPlugin): items + contesto listino/
  // versione dell'utente non devono persistere per l'eventuale utente successivo.
  userScoped: true,
})
