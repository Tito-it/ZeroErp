// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della consultazione di `dbops.error_log` (sola lettura,
//        pezzo E dell'osservabilita'): `createListaStore` con i filtri della
//        whitelist del backend e il dettaglio corrente per il drawer.
// ------------------------------------------------------------
//
// ⭐ Un registro, non una ricerca: parte pieno (`startsEmpty: false`) e si
//    legge dal piu' recente. `search` esiste solo perche' `useSearchTable` ci
//    scrive: il backend non ha ricerca testuale (i filtri sono esatti o a
//    prefisso, ognuno col suo indice — `dbops/manual/error_log.md` §indici).
// ⚠️ `tx_id` e' anche la porta del DEEP-LINK dal giornale trasversale
//    (`?tx_id=`): la view lo legge in `onActivated` e lo scrive qui.

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { listErrorLogs } from '../api/amministrazione'

export const useErrorLogStore = createListaStore('amm-error-log', {
  fetchPage: listErrorLogs,
  startsEmpty: false,
  filterDefaults: {
    area: null,
    function_name: null,
    codice: null,
    tx_id: null,
    // Floor temporale standard delle liste (oggi-60gg al 1° del mese,
    // `feedback_filtro_data_liste`): e' consultazione, non coda di lavoro.
    data_da: defaultFiltroDataDaString(),
    data_a: null,
  },
  // Allineato al preset `error_log_default` (`occurred_at desc`): il piu'
  // recente in cima; il ripiego del verso segue.
  orderBy: 'occurred_at',
  orderDir: 'desc',
  orderDirDefault: 'desc',
  extend: () => {
    // La riga aperta nel drawer di dettaglio: e' gia' nella pagina, non si
    // rilegge (non esiste un endpoint di dettaglio, e non serve).
    const rigaCorrente = ref(null)
    return { rigaCorrente }
  },
})
