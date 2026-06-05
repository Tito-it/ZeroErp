// Pinia store per la gestione soggetti (lista, CRUD, dettaglio).
// Pattern lista+CRUD via createCrudStore (regola del 2).

import { listSoggetti, getSoggetto, createSoggetto, updateSoggetto } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useSoggettiStore = createCrudStore('anagrafiche-soggetti', {
  api: { list: listSoggetti, detail: getSoggetto, create: createSoggetto, update: updateSoggetto },
  tabEntity: TAB_ENTITIES.SOGGETTO,
  filterDefaults: { tipo_soggetto_dettaglio_id: null },
  gateKeys: ['tipo_soggetto_dettaglio_id'],
  orderBy: 'ragione_sociale_completa',
})
