// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista REVISIONI DI UN PREVENTIVO (`vendite.preventivo_
//        revisioni`, tab «Revisioni» di `PreventiviDrawer`).
// Note: ⭐ Uno store SUO e non `usePreventiviStore`: quello porta la lista
//       della schermata Preventivi coi filtri dell'operatore. La forma e' la
//       factory condivisa con le offerte (`createRevisioniStore`).
//       ⚠️ `rev` dei preventivi parte da 0 (le offerte da 1): a video si vede.
// ------------------------------------------------------------
import { storePerIstanza } from '../../../core/stores/storePerIstanza'
import { createRevisioniStore } from '../../_shared/revisioni/createRevisioniStore'
import { listRevisioni } from '../api/preventiviApi'

// Uno store per drawer (`storePerIstanza`): due documenti aperti insieme non
// si scrivono addosso la catena.
export const usePreventivoRevisioniStore = storePerIstanza(
  'vendite-preventivo-revisioni',
  (id) => createRevisioniStore(id, { fetchRevisioni: listRevisioni, orderBy: 'rev' }),
)
