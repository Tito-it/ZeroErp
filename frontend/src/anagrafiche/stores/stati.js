// Pinia store per la gestione stati/nazioni (lista, CRUD).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listStati, createStato, updateStato } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useStatiStore = createCrudStore('anagrafiche-stati', {
  api: { list: listStati, create: createStato, update: updateStato },
  tabEntity: TAB_ENTITIES.STATO,
  startsEmpty: false,
})
