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
  // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
  //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
  //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
  //    l'intestazione.
  startsEmpty: false,
  filterDefaults: { attivo: true, partecipa_promo: null },
})
