// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le etichette dei vocabolari chiusi del dominio incassi, in un posto
//        solo — e le liste di opzioni che ne derivano.
// Note: ⭐ Estratto il 2026-08-28 alla rilettura critica: la stessa riga
//       (`labelOrCode(t, te, \`prefisso_${minuscolo}\`, valore)`) era scritta in
//       OTTO componenti, e tre di quei prefissi comparivano DUE volte ciascuno
//       (verso del credito, tipo di canale, destinazione). Non e' rumore: due
//       copie divergono alla prima chiave rinominata, e la copia rimasta
//       indietro mostra un CODICE dove l'altra mostra una parola — cioe' il
//       difetto si vede solo su una delle due schermate.
//
//       ⛔ E' una FABBRICA, non un oggetto condiviso: ogni chiamante ottiene le
//       proprie funzioni legate al proprio `useI18n()`. Esportare un oggetto
//       gia' costruito legherebbe tutti al `t` del primo montato, e al cambio
//       lingua il secondo consumatore resterebbe indietro **in silenzio**
//       (memoria feedback_estrarre_non_condividere_stato).
//
//       ⚠️ Ogni etichetta e' **fail-visible**: un valore che il backend aggiunge
//       e i locales non conoscono si vede come CODICE, mai come cella vuota.
// ------------------------------------------------------------

import { useI18n } from 'vue-i18n'

import { labelOrCode } from '../core/utils/i18nLabel'
import {
  CHI_E_IN_CREDITO,
  DESTINAZIONI,
  MOTIVI_FUORI_CAPIENZA,
  ORIGINI_DISTINTA,
  ROTTA_PER_CODA,
  STATI_SISTEMAZIONE,
  TIPI_CANALE,
} from './vocabolari'

export function useEtichettePagamenti() {
  const { t, te } = useI18n()

  // Scopo: la forma unica di tutte le etichette del dominio.
  const etichetta = (prefisso, valore) =>
    labelOrCode(t, te, `${prefisso}_${String(valore).toLowerCase()}`, valore)

  // Scopo: da un vocabolario a una lista di opzioni per `<Select>`.
  const opzioni = (valori, fn) => valori.map((v) => ({ value: v, label: fn(v) }))

  const credito = (v) => etichetta('pagamenti.eccedenze.credito', v)
  const tipoCanale = (v) => etichetta('pagamenti.canali.tipo', v)
  const destinazione = (v) => etichetta('pagamenti.sistemazioni.destinazione', v)
  const statoSistemazione = (v) => etichetta('pagamenti.sistemazioni.stato', v)
  const origineDistinta = (v) => etichetta('pagamenti.distinte.origine', v)
  const motivoFuoriCapienza = (v) =>
    etichetta('pagamenti.rate_fuori_capienza.motivo', v)
  const coda = (v) => etichetta('pagamenti.righe.coda', v)

  return {
    etichetta,
    credito,
    tipoCanale,
    destinazione,
    statoSistemazione,
    origineDistinta,
    motivoFuoriCapienza,
    coda,
    opzioniCredito: () => opzioni(CHI_E_IN_CREDITO, credito),
    opzioniTipoCanale: () => opzioni(TIPI_CANALE, tipoCanale),
    opzioniDestinazione: () => opzioni(DESTINAZIONI, destinazione),
    opzioniStatoSistemazione: () => opzioni(STATI_SISTEMAZIONE, statoSistemazione),
    opzioniOrigineDistinta: () => opzioni(ORIGINI_DISTINTA, origineDistinta),
    opzioniMotivoFuoriCapienza: () =>
      opzioni(MOTIVI_FUORI_CAPIENZA, motivoFuoriCapienza),
    // ⭐ Le code si derivano dalle ROTTE, non da un elenco scritto a mano: cosi'
    //    «quante sono le porte» resta vero per costruzione. `TUTTE` fa parte del
    //    vocabolario dell'endpoint ma non ha una rotta, e offrirla darebbe una
    //    voce che porta in una pagina che non esiste.
    opzioniCoda: () => opzioni(Object.keys(ROTTA_PER_CODA), coda),
  }
}
