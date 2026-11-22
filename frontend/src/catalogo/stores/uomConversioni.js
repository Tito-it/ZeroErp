// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista CONVERSIONI DI UNA UNITA' DI MISURA
//        (`catalogo.conversioni_uom` filtrata su `uom_id`, da o verso),
//        consumata da `UomConversioniDrawer` attraverso `useDrawerTabLista`.
// Note: ⭐ E' UNO STORE SUO, non `useConversioniUomStore`: quello porta la
//       lista della schermata Conversioni coi filtri dell'operatore, e
//       condividerlo scriverebbe i filtri di una schermata nell'altra
//       (`feedback_estrarre_non_condividere_stato`).
//       ⭐ La UoM e' il PADRE (contesto), non un filtro; il backend la riceve
//       come `uom_id`, lo stesso filtro della lista Conversioni.
//       ⚠️ Nessun filtro `attivo`: il drawer ha sempre mostrato tutte le
//       conversioni della UoM, e il catalogo porta la colonna «Attivo».
//       ⛔ Prima (fino al 2026-09-26) il drawer chiedeva `limit: 200` senza
//       paginator: oltre la 200ª conversione le righe sparivano senza avviso.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { listConversioniUom } from '../api/catalogo'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useUomConversioniStore = storePerIstanza('catalogo-uom-conversioni', (id) => createListaStore(id,
  {
    fetchPage: (uomId, params) => listConversioniUom({ ...params, uom_id: uomId }),
    parentField: 'uomId',
    startsEmpty: false,
    // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
    //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
    //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
    //    l'intestazione.
  },
))
