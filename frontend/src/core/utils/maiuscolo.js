// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il MAIUSCOLO MENTRE SI DIGITA, in un punto solo: la forma del testo e
//        la riscrittura dell'input col cursore rimesso dov'era.
//        Nasce il 2026-11-24 (brief-be-fe-BB-audit §7.1 F-2, regola del 2, ok
//        Tid): fino a quel giorno lo facevano `InputMaiuscolo` (codice SDI,
//        estensione del civico), che rimetteva il cursore, e
//        `normalizeUpperNoSpaces` di `string.js` (IBAN, codice fiscale, codice
//        dell'emittente), che non lo faceva: chi correggeva una lettera in mezzo
//        a un IBAN si ritrovava a scrivere in fondo.
//        Due consumatori: `InputMaiuscolo` (un `InputText`) e l'IBAN di
//        `ContoBancarioForm`, che e' un `AutoComplete` e non puo' essere un
//        `InputMaiuscolo`.
//
// ⭐ E' un aiuto di digitazione, non una regola: la forma del valore la decide
//    il DB (CHECK e guard), che risponde col campo in errore.
// ⛔ Il `codice` delle anagrafiche NON passa di qui: il DB lo salva in
//    `upper(btrim())` e la classe `app-codice-input` lo mostra soltanto
//    (frontend-standards, catalogo BB `app-codice-input`).
// ------------------------------------------------------------

import { nextTick } from 'vue'

// Scopo: il testo in maiuscolo; con `senzaSpazi` senza nessuno spazio (IBAN e
//        codice fiscale si scrivono anche a gruppi, ma il valore e' uno).
export function formaMaiuscola(testo, { senzaSpazi = false } = {}) {
  const maiuscolo = (testo || '').toUpperCase()
  return senzaSpazi ? maiuscolo.replace(/\s/g, '') : maiuscolo
}

// Scopo: il valore appena digitato in `input`, in forma maiuscola. Se la forma
//        cambia il testo, Vue riassegna il valore e il cursore salta in fondo:
//        lo si rimette dov'era, contando solo i caratteri che restano (gli
//        spazi tolti prima del cursore lo spostano indietro).
export function riscriviDigitato(input, scritto, opzioni = {}) {
  const testo = scritto || ''
  const nuovo = formaMaiuscola(testo, opzioni)
  const inizio = input?.selectionStart
  const fine = input?.selectionEnd
  if (nuovo !== testo && inizio != null && fine != null) {
    const nuovoInizio = formaMaiuscola(testo.slice(0, inizio), opzioni).length
    const nuovaFine = formaMaiuscola(testo.slice(0, fine), opzioni).length
    nextTick(() => input.setSelectionRange(nuovoInizio, nuovaFine))
  }
  return nuovo
}
