// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA FORMA DELLA SIGLA di un emittente, specchio di un vincolo che il DB
//        ha davvero: `chk_emittenti_fiscali_codice_forma` + il guard che da' la
//        frase (`anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma`,
//        2026-08-31). La usa `EmittenteFiscaleDrawer` per accendere il Salva.
//
// ⚠️ Perche' cosi' corta: dal 2026-08-31 la sigla sta DENTRO il codice commessa
//    — `CMM-<sigla>-<anno>-<9 cifre>` — che si legge separando sui trattini. E
//    il `codice` e' IMMUTABILE dopo la create: una sigla sbagliata non si
//    corregge piu'.
// ⛔ Le MINUSCOLE sono in forma. Il maiuscolo lo alza il DB (`upper(btrim())`)
//    e il campo lo mostra soltanto (`app-codice-input`): dal 2026-11-24 il
//    valore non si riscrive piu' in JavaScript (brief-be-fe-BB-audit F-2). Una
//    regola `[A-Z0-9]` sul valore digitato teneva spento il Salva a chi
//    scriveva `acme` vedendo `ACME`.
// ⛔ I due numeri NON si scrivono qui: vengono da `FIELD_LENGTH`, la sede dei
//    vincoli di lunghezza campo, perche' servono anche a `maxlength` e alla
//    frase dell'hint.
// ------------------------------------------------------------
import { FIELD_LENGTH } from '../core/constants'

const CODICE_EMITTENTE_RE = new RegExp(
  `^[A-Z0-9]{${FIELD_LENGTH.EMITTENTE_CODICE_MIN},${FIELD_LENGTH.EMITTENTE_CODICE_MAX}}$`,
  'i'
)

// Scopo: vero se `codice`, ripulito dagli spazi in testa e in coda, ha la forma
//        che il DB accetta (lettere e cifre, nella lunghezza dichiarata).
export function codiceEmittenteInForma(codice) {
  return CODICE_EMITTENTE_RE.test((codice || '').trim())
}
