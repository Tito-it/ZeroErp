// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La fabbrica delle etichette del dominio magazzino, tutte fail-visible
//        via `labelOrCode`: lo stato del documento interno, l'esito del piano,
//        la sorgente di un movimento — e le liste di opzioni per i `<Select>`.
// Note: ⭐ Fabbrica e non oggetto (come `useEtichettePagamenti`): un oggetto
//       condiviso legherebbe tutti i consumatori al `t` del primo montato.
//       ⚠️ Le chiavi sono COSTRUITE DINAMICAMENTE (`${prefisso}.${valore}`):
//       `check_i18n_keys` le dichiara punto cieco, quindi il presidio che
//       ogni valore di ogni vocabolario risolva una chiave nei locales VERI e'
//       `etichette.spec.js` — la stessa forma di `pagamenti/etichette.spec.js`.
// ------------------------------------------------------------

import { useI18n } from 'vue-i18n'

import { labelOrCode } from '../core/utils/i18nLabel'
import { ESITI_PIANO, SORGENTI_MOVIMENTO, STATI_DOCUMENTO_INTERNO } from './vocabolari'

// Le radici delle chiavi, in un posto solo: se una cambia qui e nei locales
// no, lo spec lo vede.
export const PREFISSO_STATO_DOCUMENTO = 'magazzino.documenti_interni.stato'
export const PREFISSO_ESITO_PIANO = 'magazzino.piano.esito'
export const PREFISSO_SORGENTE_MOVIMENTO = 'magazzino.movimenti.sorgente'

export function useEtichetteMagazzino() {
  const { t, te } = useI18n()

  // Scopo: la forma unica di tutte le etichette del dominio — il codice resta
  //        MAIUSCOLO nella chiave (`stato.DRAFT`), come lo emette il DB e come
  //        lo cita `types.py`: una chiave minuscola sarebbe una traduzione in
  //        piu' fra il dato e la sua etichetta.
  const etichetta = (prefisso, valore) =>
    labelOrCode(t, te, `${prefisso}.${valore}`, valore)

  // Scopo: da un vocabolario a una lista di opzioni per `<Select>`.
  const opzioni = (valori, fn) => valori.map((v) => ({ value: v, label: fn(v) }))

  const statoDocumento = (v) => etichetta(PREFISSO_STATO_DOCUMENTO, v)
  const esitoPiano = (v) => etichetta(PREFISSO_ESITO_PIANO, v)
  const sorgenteMovimento = (v) => etichetta(PREFISSO_SORGENTE_MOVIMENTO, v)

  return {
    etichetta,
    statoDocumento,
    esitoPiano,
    sorgenteMovimento,
    opzioniStatoDocumento: () => opzioni(STATI_DOCUMENTO_INTERNO, statoDocumento),
    opzioniEsitoPiano: () => opzioni(ESITI_PIANO, esitoPiano),
    opzioniSorgenteMovimento: () => opzioni(SORGENTI_MOVIMENTO, sorgenteMovimento),
  }
}
