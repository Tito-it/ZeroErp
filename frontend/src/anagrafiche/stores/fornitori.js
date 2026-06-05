// Pinia store per la gestione fornitori (lista, creazione, dettaglio, aggiornamento).
// Pattern lista+CRUD via createCrudStore (regola del 2).

import { listFornitori, getFornitore, createFornitore, updateFornitore } from '../api/anagrafiche'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useFornitoriStore = createCrudStore('anagrafiche-fornitori', {
  api: { list: listFornitori, detail: getFornitore, create: createFornitore, update: updateFornitore },
  tabEntity: TAB_ENTITIES.FORNITORE,
  filterDefaults: { stato_fornitore_id: null, attivo: null },
  gateKeys: ['stato_fornitore_id', 'attivo'],
  orderBy: 'ragione_sociale_completa',
})
