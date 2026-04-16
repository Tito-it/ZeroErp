// Store Pinia admin per anagrafiche.categorie_clienti.
// Pattern: factory `createCrudAdminStore` (v. core/composables).
import { createCrudAdminStore } from '../../core/composables/createCrudAdminStore'
import {
  listCategorieClienti,
  getCategoriaCliente,
  createCategoriaCliente,
  updateCategoriaCliente
} from '../api/categorieClienti'

export const useCategorieClientiStore = createCrudAdminStore({
  storeName: 'amministrazione-categorie-clienti',
  api: {
    list: listCategorieClienti,
    get: getCategoriaCliente,
    create: createCategoriaCliente,
    update: updateCategoriaCliente
  },
  defaultOrderBy: 'ordinamento',
  defaultOrderDir: 'asc',
  emitKey: 'categorie_clienti',
  extraFilters: {
    partecipa_promo: 'partecipa_promo'
  }
})
