// Pinia store per la gestione indirizzi dettaglio (lista, CRUD).
//
// ⭐ Dal 2026-09-18 e' `createCrudStore` e basta: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams` (search >= 3,
//    `comune_id`, limit/offset, ordinamento col ripiego) — la stessa forma che
//    la factory scrive per tutti. La lista parte VUOTA: richiede una ricerca o
//    il filtro comune (`gateKeys`), ed e' la regola empty-state standard.
// ⚠️ L'id dell'indirizzo creato NON si chiama `id`: `createIdField` lo dice
//    alla factory, che altrimenti notificherebbe le altre tab con `undefined`.

import { createCrudStore } from '../../core/stores/createCrudStore'
import { listIndirizzi, createIndirizzo, updateIndirizzo } from '../api/anagrafiche'
import { TAB_ENTITIES } from '../../core/constants'

export const useIndirizziStore = createCrudStore('anagrafiche-indirizzi', {
  api: { list: listIndirizzi, create: createIndirizzo, update: updateIndirizzo },
  tabEntity: TAB_ENTITIES.INDIRIZZO,
  createIdField: 'indirizzo_dettaglio_id',
  filterDefaults: { comune_id: null },
  gateKeys: ['comune_id'],
  // Nessun ordinamento di partenza: lo decide il backend finche' l'operatore
  // non clicca un'intestazione.
  orderDir: null,
})
