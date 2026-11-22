// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista «Di sistema» dell'area Accessi
//        (`anagrafiche.accessi_sistema`): gli utenti tecnici dei processi
//        automatici e le credenziali API_CLIENT. Sola lettura (A-6): il
//        proprietario di queste credenziali e' il pannello dei processi.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { listAccessiSistema } from '../api/amministrazione'

export const useAccessiSistemaStore = createListaStore('amm-accessi-sistema', {
  fetchPage: listAccessiSistema,
  startsEmpty: false,
  filterDefaults: { tipo: null, identita_attiva: null, bloccata: null },
  // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
  //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
  //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
  //    l'intestazione.
})
