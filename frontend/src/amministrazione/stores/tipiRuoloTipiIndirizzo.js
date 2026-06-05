// Store Pinia per la gestione della matrice config.tipi_ruolo_tipi_indirizzo (admin).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.
import {
  listTipiRuoloTipiIndirizzo,
  getTipoRuoloTipoIndirizzo,
  createTipoRuoloTipoIndirizzo,
  updateTipoRuoloTipoIndirizzo
} from '../api/tipiRuoloTipiIndirizzo'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useTipiRuoloTipiIndirizzoStore = createCrudStore('amministrazione-tipi-ruolo-tipi-indirizzo', {
  api: {
    list: listTipiRuoloTipiIndirizzo,
    detail: getTipoRuoloTipoIndirizzo,
    create: createTipoRuoloTipoIndirizzo,
    update: updateTipoRuoloTipoIndirizzo,
  },
  tabEntity: TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO,
  orderBy: 'tipo_ruolo_descrizione',
  startsEmpty: false,
  filterDefaults: { attivo: true, tipo_ruolo_id: null, tipo_indirizzo_id: null },
})
