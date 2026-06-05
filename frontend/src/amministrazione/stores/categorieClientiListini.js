// Store Pinia admin per la matrice anagrafiche.categorie_clienti_listini.
// Pattern lista+CRUD via createCrudStore (regola del 2) — lista parte piena.
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'
import {
  listCategorieClientiListini,
  getCategoriaClienteListino,
  createCategoriaClienteListino,
  updateCategoriaClienteListino
} from '../api/categorieClientiListini'

export const useCategorieClientiListiniStore = createCrudStore('amministrazione-categorie-clienti-listini', {
  api: {
    list: listCategorieClientiListini,
    detail: getCategoriaClienteListino,
    create: createCategoriaClienteListino,
    update: updateCategoriaClienteListino
  },
  tabEntity: TAB_ENTITIES.CATEGORIE_CLIENTI_LISTINI,
  orderBy: 'valido_dal',
  orderDir: 'desc',
  startsEmpty: false,
  filterDefaults: {
    attivo: true,
    categoria_cliente_id: null,
    utility_id: null,
    emittente_soggetto_ruolo_id: null,
    listino_id: null,
  },
})
