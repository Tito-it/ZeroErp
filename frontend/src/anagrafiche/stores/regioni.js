// Pinia store per la gestione regioni (lista, CRUD).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listRegioni, createRegione, updateRegione } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useRegioniStore = createCrudStore('anagrafiche-regioni', {
  api: { list: listRegioni, create: createRegione, update: updateRegione },
  tabEntity: TAB_ENTITIES.REGIONE,
  startsEmpty: false,
  filterDefaults: { stato_id: null },
})
