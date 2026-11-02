// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista «Altri accessi» dell'area Accessi
//        (`anagrafiche.accessi_altri`): le credenziali di persone senza veste
//        operatore — clienti e fornitori del portale, clienti dello shop — e
//        quelle senza alcuna veste (brief-db-be-fe-area-accessi).
// Note: `createListaStore` e non `createCrudStore`: la lista NON possiede le
//       vesti che mostra (si governano dalla scheda del cliente o del
//       fornitore, A-4); le azioni della credenziale vivono nel drawer.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { listAccessiAltri } from '../api/amministrazione'

export const useAccessiAltriStore = createListaStore('amm-accessi-altri', {
  fetchPage: listAccessiAltri,
  // Parte piena, come la lista operatori: e' il censimento degli accessi, e
  // una credenziale senza vesti deve vedersi senza doverla cercare.
  startsEmpty: false,
  filterDefaults: {
    ruolo_applicativo: null,
    stato_accesso: null,
    nessun_accesso: null,
    secondo_fattore_stato: null,
    bloccata: null,
  },
  orderBy: 'nome_visualizzato',
})
