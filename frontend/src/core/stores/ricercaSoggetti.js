// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della RICERCA UNIVERSALE dei soggetti
//        (`anagrafiche.ricerca_soggetti`, lista 113), consumato da
//        `SearchDrawer` (2026-10-31, brief-db-liste-datatable-grezze-secondo-
//        giro riga 6: prima una `DataTable` grezza con paginazione a mano).
// Note: ⭐ Parte VUOTA e legge solo con un termine (`startsEmpty`, senza
//       `gateKeys`): l'endpoint vuole `q`, e il tipo ruolo da solo non e' una
//       ricerca.
//       ⚠️ L'endpoint chiama il termine `q` (la funzione DB
//       `fn_search_soggetti_universale`, che sceglie lei i campi): qui si
//       traduce la `search` della lista.
// ------------------------------------------------------------

import { createListaStore } from './createListaStore'
import { ricercaSoggetti } from '../api/ricerca'

// Scopo: la pagina della ricerca, col termine nel parametro dell'endpoint.
function fetchPage({ search, ...params }) {
  return ricercaSoggetti({ ...params, q: search })
}

export const useRicercaSoggettiStore = createListaStore('core-ricerca-soggetti', {
  fetchPage,
  startsEmpty: true,
  ricercaCorta: 'svuota',
  filterDefaults: { tipo_ruolo_id: null },
  orderBy: 'ragione_sociale_completa',
  orderDir: 'asc',
})
