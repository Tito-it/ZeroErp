// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista RIGHE di una fattura (lista configurabile
//        `vendite.fattura_righe`), montato da `FatturaDrawer`
//        (brief-db-liste-righe-documento, lotto C).
// Note: la forma e' la factory condivisa `createRigheListaStore` (padre
//       composto fattura + emittente, nessun ordinamento di partenza: senza
//       richiesta il backend ordina come il documento); uno store per drawer
//       (`storePerIstanza`).
// ------------------------------------------------------------
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { createRigheListaStore } from '../_shared/righe/createRigheListaStore'
import { listRigheLista } from '../api/fatture'

export const useFatturaRigheStore = storePerIstanza(
  'vendite-fattura-righe',
  (id) => createRigheListaStore(id, { fetchPage: listRigheLista }),
)
