// Store Pinia per la gestione della matrice config.utilities_tipi_ruolo (admin).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.
import {
  listUtilitiesTipiRuolo,
  getUtilityTipoRuolo,
  createUtilityTipoRuolo,
  updateUtilityTipoRuolo,
} from '../api/utilitiesTipiRuolo'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useUtilitiesTipiRuoloStore = createCrudStore('amministrazione-utilities-tipi-ruolo', {
  api: {
    list: listUtilitiesTipiRuolo,
    detail: getUtilityTipoRuolo,
    create: createUtilityTipoRuolo,
    update: updateUtilityTipoRuolo,
  },
  tabEntity: TAB_ENTITIES.UTILITIES_TIPI_RUOLO,
  // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
  //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
  //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
  //    l'intestazione.
  startsEmpty: false,
  filterDefaults: { attivo: true, utility_id: null, tipo_ruolo_id: null },
  // ⚠️ La sotto-risorsa «dove e' usata questa riga» non sta piu' qui (era
  //    `fetchUsage`, fino al 2026-09-27): e' una lista a catalogo col suo
  //    store, `useUtilityTipoRuoloUsageStore`.
})
