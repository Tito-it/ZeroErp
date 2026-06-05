// Store Pinia admin per anagrafiche.categorie_clienti.
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'
import {
  listCategorieClienti,
  getCategoriaCliente,
  createCategoriaCliente,
  updateCategoriaCliente
} from '../api/categorieClienti'

export const useCategorieClientiStore = createCrudStore('amministrazione-categorie-clienti', {
  api: {
    list: listCategorieClienti,
    detail: getCategoriaCliente,
    create: createCategoriaCliente,
    update: updateCategoriaCliente
  },
  tabEntity: TAB_ENTITIES.CATEGORIE_CLIENTI,
  orderBy: 'ordinamento',
  orderDir: 'asc',
  startsEmpty: false,
  filterDefaults: { attivo: true, partecipa_promo: null },
})
