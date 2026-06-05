// Pinia store per la gestione toponomastica (tipi strada).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listToponomastica, createToponomastica, updateToponomastica } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useToponomasticaStore = createCrudStore('anagrafiche-toponomastica', {
  api: { list: listToponomastica, create: createToponomastica, update: updateToponomastica },
  tabEntity: TAB_ENTITIES.TOPONOMASTICA,
  startsEmpty: false,
})
