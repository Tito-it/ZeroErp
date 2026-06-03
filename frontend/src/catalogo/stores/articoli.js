// Store Pinia per la gestione articoli catalogo.
// Pattern lista+CRUD via createCrudListStore (regola del 2) + azioni disattiva/riattiva.

import {
  listArticoli, getArticolo, createArticolo, updateArticolo,
  disattivaArticolo, riattivaArticolo,
} from '../api/catalogo'
import { createCrudListStore } from '../../core/stores/createCrudListStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useArticoliStore = createCrudListStore('catalogo-articoli', {
  api: { list: listArticoli, detail: getArticolo, create: createArticolo, update: updateArticolo },
  tabEntity: TAB_ENTITIES.ARTICOLO,
  // attivo: default true, inviato sempre ma NON conta per il gate lista-vuota
  // (non e' in gateKeys) — comportamento preservato esatto.
  filterDefaults: { attivo: true, is_composito: null, tipo_voce_id: null, gruppo_voce_id: null },
  gateKeys: ['is_composito', 'tipo_voce_id', 'gruppo_voce_id'],
  orderBy: 'descrizione',
  extraActions: { disattiva: disattivaArticolo, riattiva: riattivaArticolo },
})
