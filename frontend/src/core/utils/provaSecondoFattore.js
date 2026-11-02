// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA PROVA del secondo fattore, cioe' cio' che il chiamante passa alle
//        API di `core/api/secondoFattore.js`: il codice dell'app OPPURE un
//        codice di recupero, mai entrambi.
// Note: nasce il 2026-10-02 (regola del 2, decisione di Tid): la stessa scelta
//       `usaRecupero ? { codiceRecupero } : { codice }` stava nel secondo passo
//       del login (LoginView) e nella disattivazione (SicurezzaView). Si usa
//       in coppia col campo `CodiceSecondoFattoreInput`, che tiene i due
//       valori `codice` / `usaRecupero`.
// ------------------------------------------------------------

// Scopo: `{ codice }` oppure `{ codiceRecupero }`, secondo cosa l'utente ha
//        scelto di inserire. Il nome della chiave e' il contratto delle API,
//        che traducono in `codice` / `codice_recupero` sul filo.
export function provaSecondoFattore(codice, usaRecupero) {
  return usaRecupero ? { codiceRecupero: codice } : { codice }
}
