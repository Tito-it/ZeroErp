// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della lista VERSIONI DI UN LISTINO
//        (`vendite.listini_versioni`, lista 112), consumato da
//        `ListinoVersioniTab` attraverso `useDrawerTabLista` (2026-10-31,
//        brief-db-liste-datatable-grezze-secondo-giro riga 5: fino a quel
//        giorno una `DataTable` nella riga espansa della lista listini, con
//        la collezione intera di ogni listino della pagina caricata insieme).
// Note: ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `listinoId` e' il path
//       dell'endpoint. I verbi delle versioni (attiva, chiudi, clona, elimina,
//       nuova) restano nei loro dialog e drawer: questo store LEGGE.
//       ⚠️ `userScoped: true` (default): i listini sono del perimetro
//       dell'emittente.
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { listVersioni } from '../api/listini'

export const useListinoVersioniStore = createListaStore('vendite-listino-versioni', {
  fetchPage: listVersioni,
  parentField: 'listinoId',
  // Il listino e' gia' scelto quando il tab si apre.
  startsEmpty: false,
  // Il preset 112: la piu' recente in cima.
  orderBy: 'valido_dal',
  orderDir: 'desc',
})
