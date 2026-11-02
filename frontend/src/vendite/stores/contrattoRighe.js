// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista RIGHE di un contratto (lista configurabile
//        `vendite.contratto_righe`), montato da `ContrattoRigheDrawer`
//        (brief-db-liste-righe-documento, lotto D).
// Note: la forma e' la factory condivisa `createRigheListaStore` (padre
//       composto contratto + emittente, nessun ordinamento di partenza: senza
//       richiesta il backend ordina per codice articolo, perche' le righe del
//       listino non hanno un numero di riga); uno store per drawer
//       (`storePerIstanza`).
//       ⭐ Una sorgente per le due forme del contratto: senza listino la
//       funzione del DB risponde le sole aggiunte, e qui non si decide niente
//       per forma.
// ------------------------------------------------------------
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { createRigheListaStore } from '../_shared/righe/createRigheListaStore'
import { listRigheLista } from '../api/contratti'

export const useContrattoRigheStore = storePerIstanza(
  'vendite-contratto-righe',
  (id) => createRigheListaStore(id, { fetchPage: listRigheLista }),
)
