// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Dopo l'annullo di un documento con legami, avvisa i tab dei documenti
//        che possono essersi riaperti (brief-db-annullo-documento-con-legami):
//        l'ordine torna da evadere, il reso da ri-consegnare, il preventivo da
//        ordinare, l'offerta da trasformare. Dall'annullo della commessa
//        (brief-db-annullo-a-valle-riapre-a-monte) anche il contratto e la
//        bolla tornano da mandare in commessa, il reso da accreditare.
// Note: ⭐ Regola del 2: la stessa lista serviva agli store di bolla, ordine,
//       preventivo e contratto. Id nullo: quale documento si e' riaperto lo
//       sa il DB; ai tab basta sapere che la loro lista puo' essere cambiata
//       (stampo di `resi.conferma`).
//       ⚠️ Le righe di commessa non hanno un tab: la commessa si rilegge
//       quando si apre. ⚠️ I consumi non hanno un tab: la loro coda si
//       rilegge quando si apre.
// ------------------------------------------------------------
import { TAB_ENTITIES } from '../../../core/constants'

const DOCUMENTI_CHE_SI_RIAPRONO = Object.freeze([
  TAB_ENTITIES.ORDINE,
  TAB_ENTITIES.RESO,
  TAB_ENTITIES.PREVENTIVO,
  TAB_ENTITIES.OFFERTA_COMMERCIALE,
  TAB_ENTITIES.CONTRATTO,
  TAB_ENTITIES.DDT,
])

// Scopo: un avviso per ogni tab dei documenti che l'annullo puo' riaprire.
//        `emitDataChanged` e' quello dello store chiamante (useTabEvents).
export function avvisaDocumentiCollegati(emitDataChanged) {
  for (const entita of DOCUMENTI_CHE_SI_RIAPRONO) emitDataChanged(entita, null)
}
