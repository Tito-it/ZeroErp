// Store Pinia admin per vendite.promo_articoli (STADIO 0 resolver v5).
// Pattern: factory `createCrudAdminStore` (v. core/composables).
import { createCrudAdminStore } from '../../core/composables/createCrudAdminStore'
import {
  listPromoArticoli,
  getPromoArticolo,
  createPromoArticolo,
  updatePromoArticolo
} from '../api/promoArticoli'

export const usePromoArticoliStore = createCrudAdminStore({
  storeName: 'vendite-promo-articoli',
  api: {
    list: listPromoArticoli,
    get: getPromoArticolo,
    create: createPromoArticolo,
    update: updatePromoArticolo
  },
  defaultOrderBy: 'valido_dal',
  defaultOrderDir: 'desc',
  emitKey: 'promo_articoli',
  extraFilters: {
    articolo_id: 'articolo_id',
    uom_id: 'uom_id',
    tipo_variazione: 'tipo_variazione'
  }
})
