// Store Pinia per la gestione listini vendite.
//
// ⭐ Dal 2026-09-18 e' `createCrudStore`: era uno store scritto a mano su
//    `useListaEmptyStateFetch` con la copia del `buildParams`.
// ⛔ Ritirati il 2026-10-31 la cache delle versioni per listino e il loro
//    preload dopo ogni pagina (N richieste per pagina): servivano alla riga
//    espansa, e le versioni sono ora la lista del tab «Versioni» del drawer
//    (`listinoVersioni`, brief-db-liste-datatable-grezze-secondo-giro riga 5).
import { createCrudStore } from '../../core/stores/createCrudStore'
import { listListini, getListino, createListino, updateListino } from '../api/listini'
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
  // Nasce a DIECI righe, come il preset (`lista_preset` 27,
  // `pagina_dimensione = 10`): al primo `config-loaded` lo scaffolding
  // allinea `filters.limit` alla `pagina_dimensione` del catalogo, che il DB
  // risolve sempre (`COALESCE(..., 25)`) — col preset a 25 il `limit` di
  // nascita durerebbe fino al primo caricamento (trovato il 18/09 sul picker
  // delle rate; frontend-standards §Dialog con una lista dentro).
  misura: USO_MISURA.COMPATTA,
  // `in_scadenza`: la regola del DB sulle versioni (il filtro del badge,
  // `AlertScadenzeWidget`); `null` = non filtra.
  filterDefaults: { utility_id: null, tipologia_id: null, attivo: true, in_scadenza: null },
  // `codice`: e' il preset default del seed della lista `vendite.listini`
  // (identificatore, colonna fissata). Il `defaultSortField` del componente
  // e' dormiente finche' questo preset esiste: la verita' e' qui.
  orderBy: 'codice',
})
