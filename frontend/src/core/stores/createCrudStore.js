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
import { useTabEvents } from '../composables/useTabEvents'
import { useListaStoreCore } from '../composables/useListaStoreCore'

// Params:
//   - api: { list, detail?, create, update } — fn che ritornano response axios
//   - tabEntity: chiave tab event bus per emitDataChanged (TAB_ENTITIES.X o stringa)
//   - createIdField: campo id dell'entita creata, per emitDataChanged (default 'id')
//   - extraActions: { nome: fn(id, ...argomenti) } azioni extra (es. disattiva/riattiva;
//       la correzione di struttura dell'articolo porta anche le colonne), wrappate con emit
//   - afterWrite: (id, azione) => void — l'aggancio post-write, chiamato dopo
//       OGNI scrittura riuscita (`create`, `update`, ogni `extraActions`) e
//       PRIMA di `emitDataChanged`: chi ascolta l'evento e ricarica deve
//       trovare gia' invalidato cio' che va invalidato. `azione` e' il nome
//       (`'create'`, `'update'`, o quello dell'azione extra). ⭐ Nasce il
//       2026-09-18 alla SECONDA occorrenza (regola del 2, ok Tid): `unitaMisura`
//       e `uomTipi` dovevano invalidare la cache del lookup (`LookupSelect` con
//       `rel=catalogo.*` la tiene in memoria) e per quella sola riga tenevano
//       il CRUD scritto a mano — tre metodi identici alla factory piu' una
//       chiamata. ⚠️ E' un aggancio, non un `extend`: l'extend AGGIUNGE, questo
//       si infila nel giro di scrittura che la factory gia' possiede.
//   - extend: (ctx) => oggetto — escape-hatch per stato/metodi custom, mergiato
//       sopra l'esposto. `ctx` e' il core INTERO (`useListaStoreCore`) piu'
//       `emitDataChanged`: quindi anche `svuota`, `reset`, `paramsFiltro`… e
//       il `fetchList` del core, che l'extend puo' avvolgere e ri-esporre col
//       suo nome (listini: il preload delle versioni dopo la pagina).
//   - options: passthrough a defineStore (default { userScoped: true })
//   - ...core: TUTTE le altre opzioni vanno a `useListaStoreCore` tal quali
//       (`filterDefaults`, `gateKeys`, `startsEmpty`, `ricercaCorta`, `orderBy`,
//       `orderDir`, `orderDirDefault`, `paramNames`, `misura`).
//       ⚠️ Passthrough e non un elenco: fino al 2026-09-18 la factory
//       ricopiava sei nomi a mano, e `limit` — nato nel core la mattina stessa —
//       qui NON arrivava. Un'opzione del core che la factory non conosce e'
//       un'opzione che lo store scrive e il BB ignora, senza nessun errore.
export function createCrudStore(storeId, {
  api,
  tabEntity,
  createIdField = 'id',
  extraActions = {},
  afterWrite = null,
  extend = null,
  options = {},
  ...core
} = {}) {
  return defineStore(storeId, () => {
    const { emitDataChanged } = useTabEvents()

    // ⭐ LO SCHELETRO DELLA LISTA VIVE IN `useListaStoreCore` dal 2026-09-02
    //    (regola del 2, ok Tid): filtri, fetch paginata, cancello empty-state,
    //    sospensione e reset erano scritti qui e ricopiati a mano da tre store
    //    che il CRUD non ce l'hanno. Qui resta solo cio' che e' CRUD.
    const lista = useListaStoreCore({ fetchPage: api.list, ...core })

    // Scopo: Dettaglio completo dell'entita.
    async function fetchDetail(id) {
      const res = await api.detail(id)
      return res.data.data
    }

    // Scopo: il giro comune di ogni scrittura riuscita — l'aggancio post-write
    //        (se dichiarato) e POI la notifica alle altre tab, in quest'ordine:
    //        chi riceve l'evento e ricarica deve trovare la cache gia' pulita.
    function dopoScrittura(id, azione) {
      if (typeof afterWrite === 'function') afterWrite(id, azione)
      emitDataChanged(tabEntity, id)
    }

    // Scopo: Crea l'entita e notifica le altre tab.
    async function create(payload) {
      const res = await api.create(payload)
      dopoScrittura(res.data.data[createIdField], 'create')
      return res.data.data
    }

    // Scopo: Aggiorna l'entita e notifica le altre tab.
    async function update(id, payload) {
      const res = await api.update(id, payload)
      dopoScrittura(id, 'update')
      return res.data.data
    }

    // ⚠️ Si riespone TUTTO il core (`fetchSospesa`, `erroreCaricamento`,
    //    `svuota`, `reset`, `paramsFiltro`) e non un sottoinsieme scelto a
    //    mano: un'esposizione parziale e' il modo in cui `fetchSospesa` era
    //    sparita dalle tre copie scritte a mano — senza rompere niente, perche'
    //    chi la legge lo fa con un guard `'fetchSospesa' in store`.
    const exposed = { ...lista, create }
    // update e fetchDetail esposti solo se l'api relativa esiste (es. comuni
    // e' create-only → niente update).
    if (typeof api.update === 'function') {
      exposed.update = update
    }
    if (typeof api.detail === 'function') {
      exposed.fetchDetail = fetchDetail
    }
    // Azioni extra (es. disattiva/riattiva): stesso giro di scrittura di
    // create/update (aggancio post-write + emitDataChanged).
    for (const [name, fn] of Object.entries(extraActions)) {
      exposed[name] = async (id, ...argomenti) => {
        const res = await fn(id, ...argomenti)
        dopoScrittura(id, name)
        return res.data.data
      }
    }
    // Escape-hatch: stato/metodi custom (sub-resource, usage, ...) con accesso
    // al core intero + emitDataChanged. Mergiati nell'exposed: chi ri-espone
    // una chiave del core (es. `fetchList` avvolto) lo fa apposta. Usato dagli
    // store admin con sotto-risorse (es. emittentiFiscali BA/utilities) e da
    // `listini` (cache versioni + preload dopo la pagina).
    if (typeof extend === 'function') {
      Object.assign(exposed, extend({ ...lista, emitDataChanged }) || {})
    }
    return exposed
  }, { userScoped: true, ...options })
}
