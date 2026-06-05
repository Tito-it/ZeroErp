// Pinia store per la gestione comuni (lista + creazione, NO update).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listComuni, createComune } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useComuniStore = createCrudStore('anagrafiche-comuni', {
  api: { list: listComuni, create: createComune },
  tabEntity: TAB_ENTITIES.COMUNE,
  startsEmpty: false,
})
