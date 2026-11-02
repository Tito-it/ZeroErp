// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Pinia store delle email dell'operatore (sola lettura), dominio Strumenti.
// ------------------------------------------------------------

// ⭐ Stessa lista del log dell'admin (`config.email_log`), un'altra porta:
//    `/core/email/log/`, aperta a ogni operatore — chi vede quale riga lo
//    decide la RLS per ambito (piano-be-fe-endpoint-senza-porta §2.3).
// ⛔ `createListaStore` e non `createCrudStore`: l'operatore non crea ne'
//    modifica un log, e un create/update che nessuno chiama e' un contratto che
//    non descrive niente. La lista e' OFFSET-based, come il BB la manda.
// ⚠️ `userScoped` di default (factory): sono le mail di QUESTO operatore, e al
//    logout non devono restare in memoria.

import { createListaStore } from '../../core/stores/createListaStore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { listEmailLog } from '../../core/api/email'

export const useEmailLogOperatoreStore = createListaStore('strumenti-email-log', {
  fetchPage: listEmailLog,
  // Parte piena: e' un registro, non una ricerca.
  startsEmpty: false,
  filterDefaults: {
    stato: null,
    // Floor temporale standard delle liste (oggi-60gg al 1° del mese).
    data_da: defaultFiltroDataDaString(),
    data_a: null,
  },
  // Il piu' recente in cima, anche quando l'operatore sceglie la colonna e
  // non il verso.
  orderBy: 'data_insert',
  orderDir: 'desc',
  orderDirDefault: 'desc',
})
