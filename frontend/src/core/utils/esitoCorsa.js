// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'ESITO DI UNA CORSA del giornale (`maintenance.job_run_log`, o la
//        coda lavori riassunta nella stessa forma), in una funzione PURA: da
//        `{saltata?, ok, ended_at}` alla faccia da mostrare — chiave i18n,
//        severity, tooltip (2026-11-22, regola del 2, ok Tid).
// Note: ⭐ Regola del 2: la stessa lettura era scritta tre volte — la cella
//        «Esito» della lista dei processi (`ProcessiAutomaticiTab`, su
//        `ultima_conclusa`), il tab «Ultime corse» del drawer del processo
//        (`ProcessoDrawer`, sulla riga del giornale) e il pannello degli esiti
//        della fatturazione (`FatturazioneEsitiPanel.esitoGiro`, su
//        `ultima_conclusa`), con chiavi i18n e rami diversi. Ritirate tutte e
//        tre nello stesso giro.
//       ⚠️ `ok` e' a TRE stati sul giornale (nullable, nessun CHECK lo lega a
//        `ended_at`), e `null` ha tre letture: corsa SALTATA (lock occupato,
//        chiusa e senza esito: la dice `saltata`), corsa ancora APERTA
//        (`ended_at` vuoto), o chiusa senza che nessuno abbia scritto
//        l'esito. Appiattirlo a rosso, o tutto a «in corso», direbbe il falso.
//       ⚠️ Su `ultima_conclusa` (`corsa_conclusa` del backend) la corsa e'
//        chiusa e mai saltata per costruzione: escono solo OK, ERRORE e
//        NON_SCRITTO. «Nessuna corsa» (`null`) e' `null` anche qui: cosa
//        mostrare al posto («mai girato», «—») lo decide chi rende.
//       ⛔ Nessun import, di proposito: e' il modulo che ha la spec (stesso
//        patto di `pallinoPresidi.js`). Le chiavi si traducono a chi rende.
// ------------------------------------------------------------

export const ESITO_CORSA = Object.freeze({
  SALTATA: 'SALTATA',
  OK: 'OK',
  ERRORE: 'ERRORE',
  IN_CORSO: 'IN_CORSO',
  NON_SCRITTO: 'NON_SCRITTO',
})

// Chiavi ESPLICITE (mai costruite: il guard i18n le deve trovare scritte).
const FACCE = Object.freeze({
  [ESITO_CORSA.SALTATA]: { chiave: 'common.corsa.saltata', severity: 'secondary', tooltip: 'common.corsa.saltata_tooltip' },
  [ESITO_CORSA.OK]: { chiave: 'common.corsa.ok', severity: 'success', tooltip: null },
  [ESITO_CORSA.ERRORE]: { chiave: 'common.corsa.errore', severity: 'danger', tooltip: null },
  [ESITO_CORSA.IN_CORSO]: { chiave: 'common.corsa.in_corso', severity: 'secondary', tooltip: null },
  [ESITO_CORSA.NON_SCRITTO]: { chiave: 'common.corsa.non_scritto', severity: 'warn', tooltip: null },
})

// Scopo: La faccia dell'esito di una corsa: `{esito, chiave, severity,
//        tooltip}`, oppure `null` se la corsa non c'e'. L'ordine dei rami e'
//        il contratto: `saltata` prima di `ok` (una saltata non ha esito), e
//        «in corso» solo quando `ok` non e' scritto.
export function esitoCorsa(corsa) {
  if (!corsa) return null
  let esito
  if (corsa.saltata === true) esito = ESITO_CORSA.SALTATA
  else if (corsa.ok === true) esito = ESITO_CORSA.OK
  else if (corsa.ok === false) esito = ESITO_CORSA.ERRORE
  else if (!corsa.ended_at) esito = ESITO_CORSA.IN_CORSO
  else esito = ESITO_CORSA.NON_SCRITTO
  return { esito, ...FACCE[esito] }
}
