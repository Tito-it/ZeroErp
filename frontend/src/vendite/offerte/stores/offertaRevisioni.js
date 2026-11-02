// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista REVISIONI DI UN'OFFERTA (`vendite.offerta_
//        revisioni`, tab «Revisioni» di `OffertaDrawer`).
// Note: ⭐ Uno store SUO e non `useOfferteStore` (la lista della schermata
//       Offerte coi filtri dell'operatore). La forma e' la factory condivisa
//       coi preventivi (`createRevisioniStore`).
//       ⚠️ L'ordinamento di partenza e' `revisione_numero`, il campo_sorgente
//       della colonna `rev` su questa lista — non `rev`, che e' il CODICE.
// ------------------------------------------------------------
import { storePerIstanza } from '../../../core/stores/storePerIstanza'
import { createRevisioniStore } from '../../_shared/revisioni/createRevisioniStore'
import { listRevisioniOfferta } from '../api/offerteApi'

// Uno store per drawer (`storePerIstanza`): due documenti aperti insieme non
// si scrivono addosso la catena.
export const useOffertaRevisioniStore = storePerIstanza(
  'vendite-offerta-revisioni',
  (id) => createRevisioniStore(id, { fetchRevisioni: listRevisioniOfferta, orderBy: 'revisione_numero' }),
)
