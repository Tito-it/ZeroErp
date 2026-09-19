// Store Pinia per la gestione righe prezzo di una versione listino.
// Gestisce paginazione server-side, filtri (search articolo, billing_account)
// e reload post-operazione (create/delete riga, variazione %).
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    una copia a mano del suo `buildParams` su `useListaEmptyStateFetch`, con
//    un wrapper di `fetchList` per il guard sul contesto che il core ha gia'.
//    Il PADRE e' la versione (`parentField: 'versioneId'`); il listino e' il
//    nonno, serve solo a comporre il path dell'endpoint e resta contesto dello
//    store — per questo non passa dalla factory, che un secondo livello di
//    path non lo sa esprimere.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { PAGINATION } from '../../core/constants'
import { listRighe } from '../api/listini'

export const useListiniRigheStore = defineStore('vendite-listini-righe', () => {
  // Il listino corrente (nonno): impostato dal drawer padre con `setContext`.
  // ⚠️ Dichiarato PRIMA del core, che lo legge nella `fetchPage`: un initializer
  //    eager incontrerebbe la TDZ del `const`.
  const listinoId = ref(null)

  // `ricercaCorta: 'ignora'`: la ricerca corta qui e' sempre stata un no-op
  // (la lista resta com'e' mentre si digita, nessuna richiesta). Nasce a
  // DIECI righe, coerente col pattern master-detail inline (frontend-standards:
  // 10 righe + rows-per-page-options [10, 25]).
  // ⛔ E IL PRESET DICE LO STESSO NUMERO (`lista_preset` 37,
  //    `pagina_dimensione = 10`): al primo `config-loaded` lo scaffolding
  //    allinea `filters.limit` alla `pagina_dimensione` del catalogo, che il
  //    DB risolve sempre (`COALESCE(..., 25)`) — col preset a 25 il `limit`
  //    di nascita durava fino al primo caricamento (trovato il 18/09 sul
  //    picker delle rate; frontend-standards §Dialog con una lista dentro).
  const lista = useListaStoreCore({
    fetchPage: (versioneId, params) => listRighe(listinoId.value, versioneId, params),
    parentField: 'versioneId',
    startsEmpty: false,
    ricercaCorta: 'ignora',
    limit: PAGINATION.COMPACT_ROWS,
    filterDefaults: { billing_account_id: null },
    orderBy: 'articolo_descrizione',
  })
  const { versioneId, filters, svuota } = lista

  // Scopo: Imposta il contesto listino/versione e azzera dati e filtri di
  //        ricerca, TENENDO ordinamento e righe per pagina (l'operatore che
  //        cambia versione non deve rifarsi l'ordine).
  // `svuota` del core, non un clear a mano: invalida anche le fetch in volo (una
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

  // ⚠️ Si riespone TUTTO il core, non un sottoinsieme (`fetchSospesa` e
  //    `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
  return { ...lista, listinoId, setContext, clearContext }
}, {
  // Reset automatico al logout (autoResetPlugin): items + contesto listino/
  // versione dell'utente non devono persistere per l'eventuale utente successivo.
  userScoped: true,
})
