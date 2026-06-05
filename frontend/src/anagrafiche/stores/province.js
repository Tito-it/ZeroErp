// Pinia store per la gestione province (lista, CRUD).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listProvince, createProvincia, updateProvincia } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useProvinceStore = createCrudStore('anagrafiche-province', {
  api: { list: listProvince, create: createProvincia, update: updateProvincia },
  tabEntity: TAB_ENTITIES.PROVINCIA,
  startsEmpty: false,
  filterDefaults: { regione_id: null },
})
