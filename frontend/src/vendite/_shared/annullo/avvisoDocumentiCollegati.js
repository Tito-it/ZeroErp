// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//       ⭐ `avvisaDopoAzione` (2026-11-14, brief-db-stati-documento-dal-
//       vocabolario FE-O2/FE-C3/FE-D3): QUANDO avvisare lo dice l'azione
//       scelta (`key` = `annulla`, l'`action_key` del passaggio), non il codice
//       della destinazione. Fino a quel giorno ogni store confrontava
//       `statoCodice === STATO_*.ANNULLATO`: quattro copie del nome dello
//       stato di annullo, che il DB legge dal vocabolario (`is_abortito`).
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

// La `key` dell'azione di annullo (`meta.action_key` dei passaggi verso lo
// stato di annullo, `config.transizioni_stati_*`): e' il verbo, lo stesso per
// ogni documento (`ASPETTO_AZIONE.annulla`).
export const AZIONE_ANNULLA = 'annulla'

// Scopo: dopo un cambio di stato, l'avviso ai documenti collegati se l'azione
//        eseguita era l'annullo. `azione`: l'entry di `available_actions`
//        scelta dall'operatore (basta la `key`).
export function avvisaDopoAzione(azione, emitDataChanged) {
  if (azione?.key === AZIONE_ANNULLA) avvisaDocumentiCollegati(emitDataChanged)
}
