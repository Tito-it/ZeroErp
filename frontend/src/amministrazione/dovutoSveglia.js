// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La cadenza del LAVORO di una sveglia calendariale, in parole:
//        «ogni lunedi' dalle 07:30 (ora dell'azienda)». `dovuto` arriva dal
//        dettaglio del processo (`{ ogni, giorno, dalle }`, brief
//        un-solo-fuso-aziendale T-9): su quelle sveglie `oncalendar` e' solo
//        la sveglia oraria, e mostrarlo direbbe «ogni ora» a un digest
//        settimanale.
// ------------------------------------------------------------
import { nomeGiornoSettimana } from '../core/utils/date'

/**
 * @param {{ogni: string, giorno: number|null, dalle: string}} dovuto
 * @param {(chiave: string, valori: object) => string} t - il `t` di vue-i18n
 * @param {string} locale - es. 'it-IT', per il nome del giorno della settimana
 * @returns {string}
 */
export function descriviDovuto(dovuto, t, locale) {
  const dalle = dovuto.dalle
  if (dovuto.ogni === 'settimana') {
    const giorno = nomeGiornoSettimana(dovuto.giorno, locale)
    return t('amministrazione.processi.sveglia_dovuto_settimana', { giorno, dalle })
  }
  if (dovuto.ogni === 'mese') {
    return t('amministrazione.processi.sveglia_dovuto_mese', { giorno: dovuto.giorno, dalle })
  }
  return t('amministrazione.processi.sveglia_dovuto_giorno', { dalle })
}
