// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store della LISTA DELLE RATE col saldo (`pagamenti.rate`, lista 68,
//        `GET /pagamenti/rate/`) — la sorgente del picker della distinta
//        (D19-c, 2026-09-17) e, domani, dello scadenzario.
// Note: ⭐ `createListaStore` e non `createCrudStore`: la lista non POSSIEDE le
//       rate che mostra — nascono col piano rate della fattura, e da qui si
//       SCELGONO. Un `create`/`update` che nessuno chiama sarebbe un contratto
//       che non descrive niente.
//
//       ⭐ PARTE VUOTA, ED E' IL CRITERIO OBBLIGATORIO del picker (D19-c): si sta
//       registrando il pagamento di QUESTO cliente, non guardando lo
//       scadenzario. Il cancello e' `startsEmpty` + `gateKeys`: senza cliente o
//       numero fattura la lista non chiede niente al backend, e lo DICE
//       (`app-empty-state` nel dialog). ⚠️ La ricerca libera (`search` >= 3,
//       che cerca il CLIENTE) conta come criterio da se', per il contratto di
//       `useListaEmptyStateFetch`: e' un terzo modo di arrivare al cliente,
//       non una scappatoia.
//
//       ⭐ ORDINE DI PARTENZA `data_scadenza ASC`, non DESC come le liste di
//       lettura: e' una CODA — la rata piu' vecchia e' quella che un pagamento
//       piu' probabilmente salda (stessa ragione dei residui di competenza). E'
//       l'`ordinamento_default` del preset a catalogo (68); il primo click
//       dell'operatore sull'intestazione resta DESC per la regola generale.
//
//       ⛔ `solo_aperte` e' un filtro del backend (`residuo <> 0`, Q-B di Tid):
//       nel picker NON si usa per nascondere le esaurite — quelle si vedono e
//       non si scelgono (brief §4.2) — ma e' qui perche' e' un filtro della
//       lista, e lo scadenzario lo accendera'.
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { listRate } from '../api/pagamenti'

export const useRateStore = createListaStore('pagamenti-rate', {
  fetchPage: listRate,
  filterDefaults: {
    billing_account_id: null,
    fattura_numero: null,
    serie: null,
    solo_aperte: null,
  },
  gateKeys: ['billing_account_id', 'fattura_numero'],
  startsEmpty: true,
  orderBy: 'data_scadenza',
  orderDir: 'asc',
})
