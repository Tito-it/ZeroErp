// Pinia store per la gestione codici postali (CAP).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.

import { listCodiciPostali, createCodicePostale, updateCodicePostale } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useCodiciPostaliStore = createCrudStore('anagrafiche-codici-postali', {
  api: { list: listCodiciPostali, create: createCodicePostale, update: updateCodicePostale },
  tabEntity: TAB_ENTITIES.CODICE_POSTALE,
  startsEmpty: false,
  filterDefaults: { comune_id: null },
})
