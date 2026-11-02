// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store della lista del PIANO di un inventario (`magazzino.inventario_
//        piano`, lista 72): che cosa il posting scrivera', posizione per
//        posizione, con l'esito e — sulle `NON_POSTABILE` — il motivo.
// Note: ⭐ Vive in un DIALOG (`InventarioPianoDialog`, `AppDialog` xl) alto
//       dieci righe (`app-dialog-lista`), quindi nasce a DIECI righe per pagina
//       (`misura: USO_MISURA.COMPATTA`) — e il preset a catalogo dice lo
//       stesso numero (frontend-standards §«Dialog con una lista dentro»).
//       ⭐ Il padre e' l'inventario (`inventarioId`, nel path dell'endpoint):
//       la lista si azzera alla chiusura del dialog, cosi' il piano del
//       documento precedente non lampeggia sotto il prossimo.
//       ⛔ Nessun ordinamento di partenza: il backend ordina per articolo e
//       poi per posizione, che e' come si legge un piano di conteggio.
//       ⚠️ Sola lettura: il piano lo calcola `fn_inventario_piano`, senza
//       vincolo di stato — in `DRAFT` e' un'anteprima, dopo `CONFIRM` la
//       fotografia contro cui si registra (D-L2-n).
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { listPiano } from '../api/magazzino'
import { USO_MISURA } from '../../core/misurePagina'

export const useInventarioPianoStore = createListaStore('magazzino-inventario-piano', {
  fetchPage: listPiano,
  parentField: 'inventarioId',
  startsEmpty: false,
  orderDir: null,
  misura: USO_MISURA.COMPATTA,
})
