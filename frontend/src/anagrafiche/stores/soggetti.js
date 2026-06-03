// Pinia store per la gestione soggetti (lista, CRUD, dettaglio).
// Pattern lista+CRUD via createCrudListStore (regola del 2).

import { listSoggetti, getSoggetto, createSoggetto, updateSoggetto } from '../api/anagrafiche'
import { createCrudListStore } from '../../core/stores/createCrudListStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useSoggettiStore = createCrudListStore('anagrafiche-soggetti', {
  api: { list: listSoggetti, detail: getSoggetto, create: createSoggetto, update: updateSoggetto },
  tabEntity: TAB_ENTITIES.SOGGETTO,
  filterDefaults: { tipo_soggetto_dettaglio_id: null },
  gateKeys: ['tipo_soggetto_dettaglio_id'],
  orderBy: 'ragione_sociale_completa',
})
