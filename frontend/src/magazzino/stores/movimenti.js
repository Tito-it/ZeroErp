// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store del REGISTRO dei movimenti di magazzino (lista
//        `magazzino.movimenti`, 77): la storia di tutto cio' che e' entrato e
//        uscito, sola lettura per costruzione (la porta e' la primitiva DB).
// Note: ⭐ Parte PIENA col floor temporale standard su `data_mov`
//       (`feedback_filtro_data_liste`): e' un archivio che si legge dal
//       recente, e il default e' `data_mov DESC, id DESC` come nel backend.
//       ⭐ I due filtri di DEEP-LINK (`inventario_id` / `rettifica_id`: i
//       movimenti nati dalle righe di QUEL documento) sono filtri come gli
//       altri, dichiarati qui — cosi' la lista puo' DIRE di essere filtrata su
//       un documento (il chip in pagina), e il chip li toglie. ⚠️ Chi li
//       applica azzera anche `data_da`: un documento registrato tre mesi fa ha
//       movimenti piu' vecchi del floor, e il deep-link mostrerebbe una lista
//       vuota per un documento che ha scritto — la stessa regola con cui
//       `useSearchTable` azzera i default temporali su una ricerca esterna.
//       ⚠️ `sorgente_tipo` e' il nome SUL FILO (`_PARAMS_MOVIMENTI` del BE);
//       nello store si chiama uguale, quindi niente `paramNames`.
//       ⛔ Nessun verbo, nessun evento cross-tab: un registro non si scrive da
//       qui, e non deve ascoltare nessuno.
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { listMovimenti } from '../api/magazzino'

export const useMovimentiStore = createListaStore('magazzino-movimenti', {
  fetchPage: listMovimenti,
  startsEmpty: false,
  filterDefaults: {
    magazzino_id: null,
    articolo_id: null,
    causale_id: null,
    sorgente_tipo: null,
    data_da: defaultFiltroDataDaString(),
    data_a: null,
    inventario_id: null,
    rettifica_id: null,
  },
  orderBy: 'data_mov',
  orderDir: 'desc',
  orderDirDefault: 'desc',
})
