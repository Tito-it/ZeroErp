// Store Pinia per la gestione conversioni UoM.
// Paginazione, sort e search sono SERVER-SIDE (2026-08-01), come le due sorelle
// uomTipi/unitaMisura: prima caricava tutto e teneva `order_by` nei filtri senza
// mai inviarlo, quindi ordinare non faceva niente e il paginator era decorativo.
//
// ⭐ Dal 2026-09-18 e' `createCrudStore` e basta: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams` — la stessa
//    forma della factory. ⚠️ Una differenza dichiarata: qui la ricerca partiva
//    a QUALUNQUE lunghezza (`if (searchTerm)`), unico caso nel frontend; ora
//    parte da tre caratteri come la policy di progetto e come le due sorelle,
//    e con 1-2 caratteri la lista resta piena (`ricercaCorta: 'fetch'`).

import { createCrudStore } from '../../core/stores/createCrudStore'
import { listConversioniUom, getConversioneUom, createConversioneUom, updateConversioneUom } from '../api/catalogo'
import { TAB_ENTITIES } from '../../core/constants'

export const useConversioniUomStore = createCrudStore('catalogo-conversioni-uom', {
  api: {
    list: listConversioniUom,
    detail: getConversioneUom,
    create: createConversioneUom,
    update: updateConversioneUom,
  },
  tabEntity: TAB_ENTITIES.CONVERSIONI_UOM,
  // Parte piena: e' un catalogo, non una ricerca.
  startsEmpty: false,
  filterDefaults: { attivo: true },
  // Regola di dominio (Tid, 2026-08-01): quando una lista mostra le date di
  // validita', `valido_al` E' l'ordinamento di default, in DESC. In Postgres
  // `DESC` porta i NULL in testa: prima le conversioni senza scadenza, poi
  // quelle con validita' piu' lunga, e in fondo le scadute — cioe' cio' che
  // vale ora sopra, cio' che non vale piu' sotto.
  //
  // ⚠️ Il preset del seed dichiara ancora `uom_from_codice asc`: allineamento
  // chiesto al team DB. Nessuno dei due e' letto dall'altro — il FE invia il
  // proprio `order_by` e `ordinamento_default` non e' ancora consumato —
  // quindi oggi vince questa riga.
  // ⚠️ Il ripiego del verso resta `asc` (default del core), com'era nella
  // copia a mano: e' un ramo dormiente, e un'estrazione appiana la
  // duplicazione, non le differenze.
  orderBy: 'valido_al',
  orderDir: 'desc',
})
