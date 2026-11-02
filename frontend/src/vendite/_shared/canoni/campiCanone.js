// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I DUE CAMPI DEL CANONE sulla testata di contratto e offerta
//        (`generazione_canone`, `mese_partenza_canone`; F-2, F-7): i campi del
//        form, da dove si riempiono e cosa parte verso il backend, e le opzioni
//        delle due tendine.
// Note: regola del 2 (brief-db-contratto-righe-periodiche-in-commessa §7.4, D-5;
//       ok Tid 2026-10-31): nati sull'offerta, il contratto li ha avuti quando
//       la madre `vendite.fn_create_contratto` li ha ammessi (`20261031-28`).
//       ⛔ I codici ammessi li dice il CHECK del DB: qui solo le etichette.
// ------------------------------------------------------------
import { GENERAZIONE_CANONE } from '../../constants'
import { nomiMesi } from '../../../core/utils/date'

// Scopo: i due campi del form, vuoti. Vuoto = «il default del DB»
//        (anticipati, da gennaio), che decide la creazione.
export function campiCanoneVuoti() {
  return { generazione_canone: null, mese_partenza_canone: null }
}

// Scopo: i due campi del form dal dettaglio salvato.
export function campiCanoneDaDettaglio(d) {
  return {
    generazione_canone: d?.generazione_canone ?? null,
    mese_partenza_canone: d?.mese_partenza_canone ?? null,
  }
}

// Scopo: la parte di richiesta dei due campi. ⛔ NOT NULL a DB col default:
//        si mandano solo valorizzati, mai `null` (la madre del contratto
//        filtra sulla PRESENZA della chiave).
export function campiCanoneDaForm(f) {
  return {
    ...(f.generazione_canone ? { generazione_canone: f.generazione_canone } : {}),
    ...(f.mese_partenza_canone ? { mese_partenza_canone: f.mese_partenza_canone } : {}),
  }
}

// Scopo: le opzioni dell'addebito dei canoni, i codici del CHECK con la loro
//        etichetta. Servono anche alla riga a canone, dove vuoto = «come la
//        testata». Chiavi i18n letterali, cosi' `check_i18n_keys` le vede.
export function opzioniGenerazioneCanone(t) {
  return [
    { value: GENERAZIONE_CANONE.INIZIO_PERIODO, label: t('vendite.canoni.generazione_canone_INIZIO_PERIODO') },
    { value: GENERAZIONE_CANONE.FINE_PERIODO, label: t('vendite.canoni.generazione_canone_FINE_PERIODO') },
  ]
}

// Scopo: i dodici mesi (valore 1-12) nella lingua data, dal BB `nomiMesi`.
export function opzioniMesePartenza(locale) {
  return nomiMesi(locale).map((nome, i) => ({ value: i + 1, label: nome }))
}
