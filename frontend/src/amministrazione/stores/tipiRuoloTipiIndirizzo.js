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
  // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
  //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
  //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
  //    l'intestazione.
  startsEmpty: false,
  filterDefaults: { attivo: true, tipo_ruolo_id: null, tipo_indirizzo_id: null },
})
