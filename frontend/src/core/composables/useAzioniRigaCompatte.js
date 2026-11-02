// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La decisione «azioni di riga a kebab» del packing responsive di
//        `ListaConfigurabile`, consegnata a `RowActionsMenu` SENZA passare
//        dal caller (provide/inject, come `useReadonlyMode`).
//
// ⭐ PERCHE' ESISTE (2026-09-29, regola del 2, ok Tid): quando lo spazio
//    stringe il packing conta per la colonna azioni la larghezza del kebab
//    (56px). Il kebab pero' si rendeva solo se il caller girava lo scope
//    `compact` dello slot `#actions` a `:force-compact`; quattordici liste non
//    lo facevano — l'esempio nel commento di `ListaConfigurabile` compreso — e
//    su desktop disegnavano i pulsanti inline, piu' larghi del conto: la
//    differenza usciva come SCROLLBAR ORIZZONTALE, senza nessun errore
//    (rilievo in-app di Tid sulle righe della distinta contabile).
//    Un contratto che ogni caller deve ricordarsi e' un difetto che aspetta:
//    ora il valore arriva da se'.
//
// ⚠️ Il provider NON e' la lista intera ma la sola CELLA AZIONI
//    (`CellaAzioniRiga`): un `RowActionsMenu` in una riga espansa o in una
//    cella `cell-*` non deve ereditare una decisione presa per un'altra
//    colonna.
// ------------------------------------------------------------

import { inject, provide } from 'vue'

export const AZIONI_COMPATTE_KEY = Symbol('appAzioniRigaCompatte')

// Provider: `compattaRef` e' un ref/computed booleano (la decisione del packing).
export function provideAzioniRigaCompatte(compattaRef) {
  provide(AZIONI_COMPATTE_KEY, compattaRef)
  return compattaRef
}

// Consumer: `null` fuori da una cella azioni di lista — cioe' nessuna
// decisione: resta lo switch CSS-first di `RowActionsMenu`.
export function useInjectAzioniRigaCompatte() {
  return inject(AZIONI_COMPATTE_KEY, null)
}
