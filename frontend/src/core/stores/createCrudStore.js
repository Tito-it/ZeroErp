// Factory unica per store Pinia CRUD-lista (lista paginata + dettaglio +
// create/update + emitDataChanged). Convergenza 2026-06-05 (regola del 2, B19)
// delle due factory gemelle pre-esistenti:
//   - createCrudListStore (core/stores)      → liste "parte-vuota" (gate)
//   - createCrudAdminStore (core/composables) → liste "parte-piena" (always-fetch)
// che ripetevano lo stesso scheletro. Entrambe ELIMINATE: questo file le
// sostituisce, delegando SEMPRE il gate a `useListaEmptyStateFetch` (che ora ha
// il modo `alwaysFetch`). L'unica vera divergenza era il gate empty-state →
// parametro `startsEmpty`.
//
// userScoped: true di DEFAULT — gli store contengono dati dell'utente loggato
// (liste scoped per emittente): vanno azzerati al logout via autoResetPlugin
// (memoria feedback_pinia_userscoped). Override via `options`.
//
// Uso (lista che parte VUOTA, es. clienti/articoli):
//   export const useClientiStore = createCrudStore('anagrafiche-clienti', {
//     api: { list, detail, create, update },
//     tabEntity: TAB_ENTITIES.CLIENTE,
//     filterDefaults: { utility_id: null, stato_cliente_id: null },
//     gateKeys: ['utility_id', 'stato_cliente_id'],
//     orderBy: 'ragione_sociale_completa',
//   })
//
// Uso (lista che parte PIENA, es. admin/config — startsEmpty:false):
//   export const useCategorieClientiStore = createCrudStore('amm-categorie-clienti', {
//     api: { list, detail, create, update },
//     tabEntity: 'categorie_clienti',
//     orderBy: 'ordinamento',
//     startsEmpty: false,
//     filterDefaults: { attivo: true, partecipa_promo: null },
//   })

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../composables/useTabEvents'
import { useListaEmptyStateFetch } from '../composables/useListaEmptyStateFetch'
import { PAGINATION } from '../constants'

// Params:
//   - api: { list, detail?, create, update } — fn che ritornano response axios
//   - tabEntity: chiave tab event bus per emitDataChanged (TAB_ENTITIES.X o stringa)
//   - filterDefaults: chiavi filtro di dominio con default (no search/limit/offset/order_*).
//       I filtri sempre-inviati-ma-non-gate (es. `attivo: true`) stanno qui e NON in gateKeys.
//   - gateKeys: sottoinsieme di filterDefaults che conta per hasFilters (gate lista-vuota).
//       Irrilevante quando startsEmpty:false.
//   - startsEmpty: true (default) → lista parte vuota (gate empty-state);
//       false → lista parte piena (always-fetch, es. admin/geo).
//   - orderBy / orderDir: ordinamento default
//   - createIdField: campo id dell'entita creata, per emitDataChanged (default 'id')
//   - extraActions: { nome: fn(id) } azioni extra (es. disattiva/riattiva), wrappate con emit
//   - options: passthrough a defineStore (default { userScoped: true })
export function createCrudStore(storeId, {
  api,
  tabEntity,
  filterDefaults = {},
  gateKeys = [],
  startsEmpty = true,
  orderBy = null,
  orderDir = 'asc',
  createIdField = 'id',
  extraActions = {},
  extend = null,
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

    const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
      filters,
      alwaysFetch: !startsEmpty,
      hasActiveFilters: (f) => gateKeys.some((k) => f[k] != null),
      buildParams: (f, searchTerm) => {
        const params = {}
        if (searchTerm.length >= 3) params.search = searchTerm
        // Invia ogni filtro di dominio valorizzato (anche quelli non-gate, es.
        // articoli.attivo / admin.attivo: default valorizzato, inviato sempre).
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
      fetchList, create,
    }
    // update e fetchDetail esposti solo se l'api relativa esiste (es. comuni
    // e' create-only → niente update).
    if (typeof api.update === 'function') {
      exposed.update = update
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
    // Escape-hatch: stato/metodi custom (sub-resource, usage, ...) con accesso
    // allo stato interno + emitDataChanged. Mergiati nell'exposed. Usato dagli
    // store admin con sotto-risorse (es. emittentiFiscali BA/utilities).
    if (typeof extend === 'function') {
      Object.assign(exposed, extend({
        emitDataChanged, filters, items, totalRecords, loading, hasSearched, fetchList,
      }) || {})
    }
    return exposed
  }, { userScoped: true, ...options })
}
