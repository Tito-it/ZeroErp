// Pinia store per la gestione clienti (lista, creazione, dettaglio).
// Pattern lista+CRUD via createCrudListStore (regola del 2).

import { listClienti, getCliente, createCliente, updateCliente } from '../api/anagrafiche'
import { createCrudListStore } from '../../core/stores/createCrudListStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useClientiStore = createCrudListStore('anagrafiche-clienti', {
  api: { list: listClienti, detail: getCliente, create: createCliente, update: updateCliente },
  tabEntity: TAB_ENTITIES.CLIENTE,
  filterDefaults: { utility_id: null, stato_cliente_id: null },
  gateKeys: ['utility_id', 'stato_cliente_id'],
  orderBy: 'ragione_sociale_completa',
})
