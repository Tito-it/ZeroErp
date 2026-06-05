// Store Pinia admin per vendite.promo_articoli (STADIO 0 resolver v5).
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'
import {
  listPromoArticoli,
  getPromoArticolo,
  createPromoArticolo,
  updatePromoArticolo
} from '../api/promoArticoli'

export const usePromoArticoliStore = createCrudStore('vendite-promo-articoli', {
  api: {
    list: listPromoArticoli,
    detail: getPromoArticolo,
    create: createPromoArticolo,
    update: updatePromoArticolo
  },
  tabEntity: TAB_ENTITIES.PROMO_ARTICOLI,
  orderBy: 'valido_dal',
  orderDir: 'desc',
  startsEmpty: false,
  filterDefaults: {
    attivo: true,
    articolo_id: null,
    uom_id: null,
    tipo_variazione: null,
  },
})
