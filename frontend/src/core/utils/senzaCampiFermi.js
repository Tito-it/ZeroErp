// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL PATCH DI UNA RIGA SCRITTA SENZA I SUOI CAMPI FERMI (2026-11-11,
//        regola del 2, ok Tid — BE21 di brief-db-revisione-catalogo).
//        `senzaCampiFermi(payload, fermo)` → un oggetto nuovo senza le chiavi
//        per cui `fermo(chiave)` risponde vero; `payload` non si tocca.
// Note: ⭐ Perche' non rimandarli «invariati»: il form li ha letti e poi
//       convertiti (un numeric(18,6) diventa Number, una data passa per una
//       `Date`). Un guard che giudica il CAMBIAMENTO (per esempio
//       `catalogo.trgfn_uom_guard_storia`) vede un valore diverso da quello
//       scritto e rifiuta una semplice chiusura. Il campo fermo non si manda.
//       ⚠️ Presuppone un PATCH PARZIALE dal lato del backend: un campo assente
//       resta com'e'.
//       ⚠️ `fermo` e' il predicato del componente (`isFieldLocked`, che in
//       creazione risponde sempre falso): la decisione resta dove nasce.
// ------------------------------------------------------------

export function senzaCampiFermi(payload, fermo) {
  return Object.fromEntries(Object.entries(payload).filter(([campo]) => !fermo(campo)))
}
