// Store Pinia admin per la matrice anagrafiche.categorie_clienti_listini.
// Pattern: factory `createCrudAdminStore` (v. core/composables).
import { createCrudAdminStore } from '../../core/composables/createCrudAdminStore'
import {
  listCategorieClientiListini,
  getCategoriaClienteListino,
  createCategoriaClienteListino,
  updateCategoriaClienteListino
} from '../api/categorieClientiListini'

export const useCategorieClientiListiniStore = createCrudAdminStore({
  storeName: 'amministrazione-categorie-clienti-listini',
  api: {
    list: listCategorieClientiListini,
    get: getCategoriaClienteListino,
    create: createCategoriaClienteListino,
    update: updateCategoriaClienteListino
  },
  defaultOrderBy: 'valido_dal',
  defaultOrderDir: 'desc',
  emitKey: 'categorie_clienti_listini',
  extraFilters: {
    categoria_cliente_id: 'categoria_cliente_id',
    utility_id: 'utility_id',
    emittente_soggetto_ruolo_id: 'emittente_soggetto_ruolo_id',
    listino_id: 'listino_id'
  }
})
