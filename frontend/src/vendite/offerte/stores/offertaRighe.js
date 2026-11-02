// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista RIGHE di un'offerta commerciale (lista
//        configurabile `vendite.offerta_righe`, 106), montato da
//        `OffertaRigheDrawer` (brief-db-righe-esclusione-solo-non-si-vende
//        §8.1, 2026-10-05). Gemello di `useContrattoRigheStore`.
// Note: la forma e' la factory condivisa `createRigheListaStore` (padre
//       composto offerta + emittente, nessun ordinamento di partenza: senza
//       richiesta il backend ordina per codice articolo, perche' le righe del
//       listino non hanno un numero di riga); uno store per drawer
//       (`storePerIstanza`).
// ------------------------------------------------------------
import { storePerIstanza } from '../../../core/stores/storePerIstanza'
import { createRigheListaStore } from '../../_shared/righe/createRigheListaStore'
import { listRigheLista } from '../api/offerteApi'

export const useOffertaRigheStore = storePerIstanza(
  'vendite-offerta-righe',
  (id) => createRigheListaStore(id, { fetchPage: listRigheLista }),
)
