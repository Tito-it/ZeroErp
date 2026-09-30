// Store Pinia per la gestione listini vendite.
//
// ⭐ Dal 2026-09-18 e' `createCrudStore` + `extend`: era uno store scritto a
//    mano su `useListaEmptyStateFetch` con la copia del `buildParams`. Nell'
//    `extend` resta cio' che e' di dominio — la cache delle versioni per
//    listino e il preload dopo ogni pagina, che avvolge il `fetchList` del
//    core e lo ri-espone col suo nome.
import { ref } from 'vue'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { listListini, getListino, createListino, updateListino, listVersioni } from '../api/listini'
import { TAB_ENTITIES } from '../../core/constants'
import { USO_MISURA } from '../../core/misurePagina'

export const useListiniStore = createCrudStore('vendite-listini', {
  api: { list: listListini, detail: getListino, create: createListino, update: updateListino },
  tabEntity: TAB_ENTITIES.LISTINO,
  // Parte piena, ma una ricerca sotto i 3 caratteri SVUOTA invece di lasciare
  // a video righe che non c'entrano con quello che si sta scrivendo: e' l'UX
  // che questa lista ha sempre avuto (`ricercaCorta`, migrazione 2026-08-10).
  startsEmpty: false,
  ricercaCorta: 'svuota',
  // Nasce a DIECI righe: ogni riga si espande sulle proprie versioni, e a 25
  // la pagina non si legge. E' l'eccezione dichiarata da `useSearchTable`
  // («le liste che nascono a 10 restano eccezioni»).
  // ⛔ E IL PRESET DICE LO STESSO NUMERO (`lista_preset` 27,
  //    `pagina_dimensione = 10`): al primo `config-loaded` lo scaffolding
  //    allinea `filters.limit` alla `pagina_dimensione` del catalogo, che il
  //    DB risolve sempre (`COALESCE(..., 25)`) — col preset a 25 il `limit`
  //    di nascita durava fino al primo caricamento (trovato il 18/09 sul
  //    picker delle rate; frontend-standards §Dialog con una lista dentro).
  misura: USO_MISURA.COMPATTA,
  filterDefaults: { utility_id: null, tipologia_id: null, attivo: true },
  // `codice`: e' il preset default del seed della lista `vendite.listini`
  // (identificatore, colonna fissata). Il `defaultSortField` del componente
  // e' dormiente finche' questo preset esiste: la verita' e' qui.
  orderBy: 'codice',
  extend: ({ items, fetchList: fetchListBase }) => {
    // Cache versioni per listino: { [listino_id]: [versione, ...] }.
    // Popolata dopo fetchList o on-expand riga; invalidata su create/update versione.
    const versioniByListino = ref({})

    // Preload versioni per i listini correnti (expansion default-aperta): resta
    // FUORI dal core perche' e' un secondo giro di fetch del dominio, non parte
    // del ciclo di lista. ⚠️ Gira dopo la finestra di `loading`: lo spinner
    // della lista si spegne un istante prima che le versioni siano in casa. Gli
    // errori del singolo listino li gestisce gia' `fetchVersioniListino`.
    // Il preload parte SOLO se la fetch ha davvero aggiornato `items`: una
    // guardia (ricerca corta) o una risposta scartata dal guard di versione non
    // devono potare la cache versioni a vuoto ne' rilanciare il preload sugli
    // id di un'altra chiamata (doppioni di N richieste versioni).
    async function fetchList(opzioni) {
      const landed = await fetchListBase(opzioni)
      if (landed) await preloadVersioniForCurrentItems()
      return landed
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
      versioniByListino,
      fetchList,
      fetchVersioniListino, preloadVersioniForCurrentItems, invalidateVersioniListino,
    }
  },
})
