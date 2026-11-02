// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista UTILIZZO DI UNA RIGA DELLA MATRICE utility ×
//        tipi ruolo (`config.utilities_tipi_ruolo_usage`, lista 86): gli
//        emittenti fiscali con un override per la stessa utility. La consuma
//        il tab «Utilizzo» di `UtilityTipoRuoloDrawer` via `useDrawerTabLista`.
// Note: ⭐ E' UNO STORE SUO, non un metodo di `useUtilitiesTipiRuoloStore`:
//       quello porta la lista della matrice coi filtri dell'operatore, e
//       condividerlo scriverebbe la pagina di una lista nell'altra
//       (`feedback_estrarre_non_condividere_stato`).
//       ⛔ Fino al 2026-09-27 il tab chiedeva `limit: 100` senza paginator:
//       oltre il centesimo emittente le righe sparivano senza avviso (brief-
//       db-liste-datatable-grezze riga 4).
//       ⚠️ Lista `multi_emittente`: ogni riga E' un emittente, e il codice e
//       la ragione sociale lo dicono. Nessun emittente da fissare, quindi il
//       padre e' la sola riga di matrice (nel path).
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { listUtilityTipoRuoloUsage } from '../api/utilitiesTipiRuolo'

// Uno store per drawer (`storePerIstanza`).
export const useUtilityTipoRuoloUsageStore = storePerIstanza(
  'amministrazione-utility-tipo-ruolo-usage',
  (id) => createListaStore(id, {
    fetchPage: listUtilityTipoRuoloUsage,
    parentField: 'recordId',
    // La riga di matrice e' gia' scelta quando il tab compare.
    startsEmpty: false,
    // ⛔ NESSUN ordinamento di partenza: senza indicazioni il backend applica
    //    quello storico del tab, a DUE criteri (ragione sociale, poi codice),
    //    che nessuna colonna sola sa esprimere.
    orderDir: null,
  }),
)
