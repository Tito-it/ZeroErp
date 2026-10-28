// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: ⭐ I PASSAGGI MANUALI CHE L'OPERATORE PUO' FARE DALLO STATO DELLA RIGA,
//        letti dal campo `azioni_permesse` che il backend porta in riga
//        (`script.fn_doc_azioni_permesse`, brief-modello-documento-vendita
//        §15.14): le `action_key` della matrice dei passaggi, gia' filtrate per
//        il permesso dell'azione. Chi non ha l'azione non vede la voce.
//
// ⛔ FAIL-CLOSED: un campo assente o non array (riga vecchia, proiezione che
//    non lo porta) vale «nessun passaggio», mai «tutti».
//
// ⛔ E' LETTURA, NON REGOLA: non deduce niente dal codice dello stato. Se il
//    passaggio si puo' fare DAVVERO lo dice il verbo del DB al click; qui si
//    decide solo se PROPORLO.
//
// Nasce il 2026-10-28 (regola del 2): la lettura era ripetuta nel lotto
// (`useLottoAzioni.verbiPlausibili`) e nella versione di listino
// (`ListiniSearchTable`).

// Scopo: le `action_key` permesse della riga; array vuoto se il campo manca.
export function azioniPermesse(riga) {
  return Array.isArray(riga?.azioni_permesse) ? riga.azioni_permesse : []
}

// Scopo: il passaggio `actionKey` e' fra quelli che l'operatore puo' fare?
export function passaggioPermesso(riga, actionKey) {
  return azioniPermesse(riga).includes(actionKey)
}
