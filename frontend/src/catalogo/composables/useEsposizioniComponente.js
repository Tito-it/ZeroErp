// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I tre modi di esporre in fattura un componente di kit
//        (`config.esposizioni_componente`: NASCOSTO / DESCRITTIVO /
//        VALORIZZATO), con l'etichetta tradotta che il DB dichiara riga per
//        riga (`etichetta_key`). Una sede per i tre consumatori: la scelta
//        nella distinta (`ArticoloBomDrawer`) e il modo per esteso nei
//        componenti di riga (`ComponentiPanel`, `ComponentiDialog`).
// Note: estratto alla seconda occorrenza (regola del 2, ok Tid 2026-10-02;
//       brief-db-esposizione-componenti-kit-in-fattura R-FE-2/R-FE-3). Il
//       codice e' il `codice_interno`, la chiave che la FK della distinta
//       valida e che anteprime e componenti portano in `esposizione_in_fattura`.
// ------------------------------------------------------------
import { useLookupEtichettato } from '../../core/composables/useLookupEtichettato'

// Il lookup generico specializzato (`etichetta_key` in piu'): stessa entry
// della cache per tutti i consumatori, quindi una sola chiamata per sessione.
const SORGENTE = { rel: 'config.esposizioni_componente' }

// Il modo che NON fa comparire il componente in fattura: e' il default della
// colonna di distinta e l'unico valore con cui il FE ragiona (il «compare in
// fattura?» di una cella). Gli altri due li distingue solo l'etichetta.
export const ESPOSIZIONE_NASCOSTO = 'NASCOSTO'

// Scopo: la gravita' del Tag di un modo: `info` se il componente compare in
//        fattura (DESCRITTIVO, VALORIZZATO), `secondary` se no. E' un fatto,
//        non uno stato: la stessa coppia di colori del Si'/No.
export function severitaEsposizione(codice) {
  return codice && codice !== ESPOSIZIONE_NASCOSTO ? 'info' : 'secondary'
}

// Scopo: le opzioni `{ value, label }` della tendina e `etichetta(codice)`
//        per la cella (ripiego sul codice grezzo, mai una cella vuota).
export function useEsposizioniComponente({ immediate = true } = {}) {
  const { opzioni, etichetta, loading, loaded } = useLookupEtichettato(SORGENTE, {
    campoCodice: 'codice_interno',
    immediate,
  })
  return { opzioni, etichetta, loading, loaded }
}
