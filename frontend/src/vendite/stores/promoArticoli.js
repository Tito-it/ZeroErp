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
  // Regola di dominio: dove una lista mostra le date di validita', `valido_al`
  // e' l'ordinamento di default, in DESC. In Postgres `DESC` porta i NULL in
  // testa: prima le promo senza scadenza, poi quelle con validita' piu' lunga,
  // e in fondo le scadute — cioe' cio' che vale ora sopra, cio' che non vale
  // piu' sotto.
  orderBy: 'valido_al',
  orderDir: 'desc',
  startsEmpty: false,
  filterDefaults: {
    attivo: true,
    articolo_id: null,
    uom_id: null,
    tipo_variazione: null,
  },
})
