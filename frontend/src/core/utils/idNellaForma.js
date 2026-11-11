// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: UN IDENTIFICATIVO NELLA FORMA CHE LA DESTINAZIONE SI ASPETTA, o `null`.
//        `idNellaForma(valore, forma)`: `INTERO` → intero > 0; `UUID` → la
//        stringa, se e' un uuid; altrimenti `null`.
// Note: estratto il 2026-11-11 (regola del 2, ok Tid) da `core/bersagli.js`
//       (`identificativo`), quando l'ha chiesto anche il deep-link `?open=`
//       delle liste (`useIngressoDaQuery`): un id arriva come TESTO (envelope,
//       query dell'URL) e diventa la prop di un drawer.
//       ⛔ LA FORMA SI DICHIARA, NON SI DEDUCE DAL VALORE: un uuid e un numero
//       si distinguono a occhio, ma la regola e' che cosa quell'entita' usa
//       come chiave. ⚠️ Non e' `config.tipi_entita.key_selector`: quello dice
//       QUALE colonna (`id` o `uid`), e `catalogo.articoli.id` e' un uuid.
//       ⚠️ Le prop `*Id` dei drawer numerici sono dichiarate `Number`: una
//       stringa e' un avviso in sviluppo e un difetto muto in produzione.
// ------------------------------------------------------------

export const FORME_ID = Object.freeze({
  INTERO: 'intero',
  UUID: 'uuid',
})

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
// ⛔ Le sole cifre decimali, senza zeri in testa: `Number()` da solo accetta
//    `'1e3'` (1000), `'0x10'` (16), `' 7 '`, `'+5'`, `'7.0'` — ognuno apre una
//    riga che nessuno ha indicato.
const INTERO_RE = /^[1-9]\d*$/

export function idNellaForma(valore, forma) {
  if (valore == null || valore === '') return null
  if (forma === FORME_ID.UUID) {
    return typeof valore === 'string' && UUID_RE.test(valore) ? valore : null
  }
  if (forma === FORME_ID.INTERO) {
    // ⛔ `> 0`, non solo «e' un numero»: `Number('0')` e `Number('-3')` sono
    //    finiti, e aprirebbero `/fatture/0/`, cioe' un 404 (AGENTS: un id
    //    numerico e' un errore se NULL o <= 0). Un array (`?open=1&open=2`) e'
    //    `NaN`, quindi `null`.
    // ⛔ `isSafeInteger`, non `isInteger`: le chiavi sono `bigint`, e oltre
    //    2^53 `Number('9007199254740993')` e' 9007199254740992 — un intero
    //    valido che apre la riga ACCANTO, senza errore. Meglio nessun pulsante.
    const n = typeof valore === 'number'
      ? valore
      : (typeof valore === 'string' && INTERO_RE.test(valore) ? Number(valore) : NaN)
    return Number.isSafeInteger(n) && n > 0 ? n : null
  }
  // Una forma sconosciuta e' un errore di chi dichiara: si scarta, in silenzio
  // in produzione, a voce in sviluppo.
  if (import.meta.env.DEV) console.warn(`[idNellaForma] forma sconosciuta «${forma}»`)
  return null
}
