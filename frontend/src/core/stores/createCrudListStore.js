// Factory per store Pinia CRUD-lista (lista paginata + dettaglio + create/update).
//
// Estrae il pattern identico ~95% di clienti/fornitori/soggetti (anagrafiche) e
// articoli (catalogo): stesso state, stessa fetchList con gate "min 3 caratteri /
// hasFilters", stessa fetchDetail, stessi create/update con emitDataChanged.
//
// userScoped: true di DEFAULT — questi store contengono dati dell'utente loggato
// (liste scoped per emittente): vanno azzerati al logout via autoResetPlugin per
// evitare leak cross-user sullo stesso browser. Allinea ai gemelli vendite
// (contratti/listini/preventivi/offerte). Override via `options`.
//
// Uso:
//   export const useClientiStore = createCrudListStore('anagrafiche-clienti', {
//     api: { list: listClienti, detail: getCliente, create: createCliente, update: updateCliente },
//     tabEntity: TAB_ENTITIES.CLIENTE,
//     filterDefaults: { utility_id: null, stato_cliente_id: null },
//     gateKeys: ['utility_id', 'stato_cliente_id'],
//   })

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../composables/useTabEvents'
import { useListaEmptyStateFetch } from '../composables/useListaEmptyStateFetch'
import { PAGINATION } from '../constants'

// Scopo: costruisce un useXxxStore per il pattern lista+CRUD parametrizzato.
//   - api: { list, detail?, create, update }
//   - tabEntity: TAB_ENTITIES.X per emitDataChanged
//   - filterDefaults: chiavi filtro di dominio con default (no search/limit/offset/order_*)
//   - gateKeys: sottoinsieme di filterDefaults che conta per hasFilters (gate lista-vuota)
//   - orderBy / orderDir: ordinamento default
//   - createIdField: campo id dell'entita creata, per emitDataChanged (default 'id')
//   - extraActions: { nome: fn(id) } azioni extra (es. disattiva/riattiva), wrappate con emit
//   - options: passthrough a defineStore (default { userScoped: true })
export function createCrudListStore(storeId, {
  api,
  tabEntity,
  filterDefaults = {},
  gateKeys = [],
  orderBy = null,
  orderDir = 'asc',
  createIdField = 'id',
  extraActions = {},
  options = {},
} = {}) {
  return defineStore(storeId, () => {
    const { emitDataChanged } = useTabEvents()

    const filters = ref({
      search: '',
      ...filterDefaults,
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      order_by: orderBy,
      order_dir: orderDir,
    })

    // Stato lista + fetchList delegati al BB `useListaEmptyStateFetch` (gate
    // empty-state single-source, 2026-06-03): la guardia "lista parte vuota,
    // richiede search >= 3 o filtro gate attivo" e' identica al composable usato
    // dai 3 store-documento vendite (offerte/preventivi/ordini). Qui restano
    // caller-owned solo `hasActiveFilters` (gateKeys) e `buildParams` (mapping
    // generico 1:1 filtri→query + limit/offset, standard CRUD-semplice).
    const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
      filters,
      hasActiveFilters: (f) => gateKeys.some((k) => f[k] != null),
      buildParams: (f, searchTerm) => {
        const params = {}
        if (searchTerm.length >= 3) params.search = searchTerm
        // Invia ogni filtro di dominio valorizzato (anche quelli non-gate, es.
        // articoli.attivo: default true, inviato sempre ma non gata la lista).
        for (const k of Object.keys(filterDefaults)) {
          if (f[k] != null) params[k] = f[k]
        }
        params.limit = f.limit
        params.offset = f.offset
        if (f.order_by) {
          params.order_by = f.order_by
          params.order_dir = f.order_dir || 'asc'
        }
        return params
      },
      fetchPage: api.list,
    })

    // Scopo: Dettaglio completo dell'entita.
    async function fetchDetail(id) {
      const res = await api.detail(id)
      return res.data.data
    }

    // Scopo: Crea l'entita e notifica le altre tab.
    async function create(payload) {
      const res = await api.create(payload)
      emitDataChanged(tabEntity, res.data.data[createIdField])
      return res.data.data
    }

    // Scopo: Aggiorna l'entita e notifica le altre tab.
    async function update(id, payload) {
      const res = await api.update(id, payload)
      emitDataChanged(tabEntity, id)
      return res.data.data
    }

    const exposed = {
      items, totalRecords, loading, hasSearched, filters,
      fetchList, create, update,
    }
    if (typeof api.detail === 'function') {
      exposed.fetchDetail = fetchDetail
    }
    // Azioni extra (es. disattiva/riattiva): wrap uniforme con emitDataChanged.
    for (const [name, fn] of Object.entries(extraActions)) {
      exposed[name] = async (id) => {
        const res = await fn(id)
        emitDataChanged(tabEntity, id)
        return res.data.data
      }
    }
    return exposed
  }, { userScoped: true, ...options })
}
