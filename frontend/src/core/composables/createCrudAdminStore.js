// Scopo: Factory per store Pinia "admin CRUD" con boilerplate standard
//        (items/totalRecords/loading/hasSearched + filters + fetchList +
//        fetchDetail + create + update + emitDataChanged).
//        Usato da: categorieClienti, categorieClientiListini, promoArticoli
//        e altri futuri admin table v5.
//
// Differenze ammesse tra istanze:
//  - storeName (chiave defineStore univoca)
//  - api (list/get/create/update)
//  - default order (campo + direzione)
//  - filtri specifici (oltre a search/attivo) con mappatura client -> param server
//  - emitKey (nome canale tab event bus)

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from './useTabEvents'

// Scopo: Crea e ritorna una funzione defineStore("...") che implementa
//        il pattern CRUD admin standard. Il risultato e' usato come
//        `export const useXyzStore = createCrudAdminStore({...})`.
//
// Params:
//  - storeName:             id pinia (stringa univoca)
//  - api:                   { list, get, create, update } — fn che ritornano
//                           axios response (envelope {data: {data: ..., meta}})
//  - defaultOrderBy:        campo ORDER BY iniziale
//  - defaultOrderDir:       'asc' | 'desc'
//  - emitKey:               chiave tab event bus (es. 'categorie_clienti')
//  - extraFilters:          oggetto { clientKey: 'serverParamName', ... } —
//                           filtri specifici che vanno solo se non-null;
//                           lo store aggiunge automaticamente a filters.value
//                           come null default.
//  - extraFilterDefaults:   override valori default per extraFilters (es.
//                           `{ partecipa_promo: null }` esplicito).
export function createCrudAdminStore({
  storeName,
  api,
  defaultOrderBy,
  defaultOrderDir = 'desc',
  emitKey,
  extraFilters = {},
  extraFilterDefaults = {},
}) {
  return defineStore(storeName, () => {
    const { emitDataChanged } = useTabEvents()

    const items = ref([])
    const totalRecords = ref(0)
    const loading = ref(false)
    const hasSearched = ref(false)

    // Inizializzazione filtri: base + default null per extra.
    const baseFilters = {
      search: '',
      attivo: true,
      limit: 25,
      offset: 0,
      order_by: defaultOrderBy,
      order_dir: defaultOrderDir,
    }
    for (const clientKey of Object.keys(extraFilters)) {
      baseFilters[clientKey] = (clientKey in extraFilterDefaults)
        ? extraFilterDefaults[clientKey]
        : null
    }
    const filters = ref({ ...baseFilters })

    async function fetchList() {
      const f = filters.value
      const searchTerm = (f.search || '').trim()
      // Search opzionale, minimo 3 char. Sotto soglia: non chiamare il BE
      // ma svuotare i risultati precedenti per coerenza UX (evita che l'utente
      // veda dati obsoleti mentre completa la digitazione).
      if (searchTerm.length > 0 && searchTerm.length < 3) {
        if (hasSearched.value) {
          items.value = []
          totalRecords.value = 0
          hasSearched.value = false
        }
        return
      }

      loading.value = true
      try {
        const params = { limit: f.limit, offset: f.offset }
        if (f.order_by) {
          params.order_by = f.order_by
          params.order_dir = f.order_dir || 'asc'
        }
        if (searchTerm.length >= 3) params.search = searchTerm
        if (f.attivo != null) params.attivo = f.attivo
        // Mappa filtri extra: clientKey -> serverParamName, solo se non null.
        for (const [clientKey, serverParam] of Object.entries(extraFilters)) {
          if (f[clientKey] != null) params[serverParam] = f[clientKey]
        }

        const res = await api.list(params)
        items.value = res.data.data.results
        totalRecords.value = res.data.data.count
        hasSearched.value = true
      } finally {
        loading.value = false
      }
    }

    async function fetchDetail(id) {
      const res = await api.get(id)
      return res.data.data
    }

    async function create(payload) {
      const res = await api.create(payload)
      emitDataChanged(emitKey, res.data.data.id)
      return res.data.data
    }

    async function update(id, payload) {
      const res = await api.update(id, payload)
      emitDataChanged(emitKey, id)
      return res.data.data
    }

    return {
      items, totalRecords, loading, hasSearched, filters,
      fetchList, fetchDetail, create, update
    }
  })
}
