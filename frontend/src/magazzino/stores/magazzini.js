// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della lista MAGAZZINI (`magazzino.magazzini`, lista 80) —
//        la lista POSSIEDE l'anagrafica: qui stanno anche i verbi (crea,
//        aggiorna, dettaglio) che avvisano le altre tab.
// Note: Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4.2.
//       ⭐ E' `createCrudStore`, la factory delle liste che possiedono la loro
//       entita' (frontend-standards §Factory `createCrudStore`): dettaglio,
//       `create`/`update` ed `emitDataChanged` sono i suoi. ⚠️ La prima
//       stesura (21-09) li riscriveva a mano su `createListaStore` + `extend`
//       — quattro metodi identici alla factory piu' una riga d'invalidazione,
//       che e' esattamente il caso per cui esiste `afterWrite`.
//       ⭐ Il PRODUCER cross-tab: ogni scrittura riuscita emette
//       `TAB_ENTITIES.MAGAZZINO` — le liste che mostrano un magazzino
//       (documenti interni, disponibilita') lo leggono dal lookup generico,
//       che `afterWrite` invalida PRIMA dell'evento (chi ricarica trova la
//       cache gia' pulita).
//       ⚠️ `userScoped: true` (default): i magazzini sono del perimetro
//       emittente dell'operatore (RLS), al logout non restano in memoria.
//       ⭐ Parte PIENA e con le sole ATTIVE: e' un'anagrafica, non una coda;
//       «Mostra non attivi» e' l'interruttore (`FiltroToggle`, `attivo: null`).
// ------------------------------------------------------------

import { TAB_ENTITIES } from '../../core/constants'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { chiaveLookupCodici } from '../../core/composables/useLookupCodici'
import { createCrudStore } from '../../core/stores/createCrudStore'
import {
  aggiornaMagazzino,
  creaMagazzino,
  getMagazzino,
  listMagazzini,
} from '../api/magazzino'
import { LOOKUP_REL_MAGAZZINI } from '../vocabolari'

export const useMagazziniStore = createCrudStore('magazzino-magazzini', {
  api: { list: listMagazzini, detail: getMagazzino, create: creaMagazzino, update: aggiornaMagazzino },
  tabEntity: TAB_ENTITIES.MAGAZZINO,
  startsEmpty: false,
  // `attivo: true` = solo le attive; l'interruttore lo porta a `null` (tutte).
  filterDefaults: { attivo: true },
  orderBy: 'codice',
  orderDir: 'asc',
  // Scopo: dopo una scrittura, i PICKER (`<LookupSelect rel="magazzino.magazzini">`
  //        del documento interno, dei filtri): la cache condivisa del lookup
  //        si invalida — nelle DUE chiavi che il `rel` puo' avere — o
  //        proporrebbe un magazzino spento o non proporrebbe quello nuovo.
  afterWrite: () => {
    invalidateLookup(chiaveLookupCodici(LOOKUP_REL_MAGAZZINI))
    invalidateLookup(chiaveLookupCodici(LOOKUP_REL_MAGAZZINI, { includiObsoleti: false }))
  },
})
