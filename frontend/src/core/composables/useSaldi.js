// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA BASE DEI SALDI — l'unica sede del frontend che legge quanto manca
//        da regolare, a qualunque livello.
// Note: ⛔ NON e' «il saldo della fattura»: e' la BASE, e la fattura e' il suo
//        primo consumatore (vincolo §2.7 del brief incassi, decisione di Tid
//        del 2026-08-24). Un saldo calcolato in due posti diverge alla prima
//        regola nuova, e sono numeri su cui qualcuno decide se sollecitare un
//        cliente. Stessa ragione per cui il pricing passa solo dal suo service.
//
//        ⭐ IL VOCABOLARIO E' UNO SOLO, e vale a ogni livello:
//          `residuo`        quanto manca ancora da regolare — la domanda che
//                           uno si fa;
//          `in_lavorazione` denaro gia' digitato su una distinta e NON ancora
//                           registrato: non abbassa il residuo, e vederlo
//                           spiega perche';
//          `incassato`      di quanto e' stato registrato, quanto e' entrato
//                           DAVVERO in banca (i giri interni sono esclusi).
//        ⛔ Una schermata sceglie QUALI numeri accendere. Nessuna li rinomina,
//        nessuna li ricalcola.
//
//        ⭐ NASCE CON TRE LIVELLI IN TESTA — documento, rata, cliente — anche se
//        il terzo si accende dopo: e' sviluppo concentrico, non YAGNI. Il
//        backend ha gia' la sua sede vuota per il cliente; quando DB-10 atterra
//        si accende **qui e li'**, e nessun'altra sede cambia.
//
//        ⚠️ E la base trova subito un DISLIVELLO: alla rata il database da'
//        tutti e tre i numeri, al documento ne da' DUE — `incassato` arriva
//        `null`. ⛔ Non si sana con una somma: `null` vuol dire «a questo
//        livello non si sa», che e' diverso da zero, e sommare per riempirlo
//        sarebbe inventare un numero su cui qualcuno decide.
// ------------------------------------------------------------

import { computed } from 'vue'

import { getSaldoFattura, getSaldoRata } from '../../pagamenti/api/pagamenti'
import { useLetturaTreStati } from './useLetturaTreStati'

// I tre livelli. ⭐ `CLIENTE` e' dichiarato e **non ancora acceso**: e' il terzo
// livello previsto dalla decisione, e sta qui perche' il giorno in cui nasce si
// veda che era atteso — non che sia stato aggiunto di corsa.
export const LIVELLO = Object.freeze({
  DOCUMENTO: 'DOCUMENTO',
  RATA: 'RATA',
  CLIENTE: 'CLIENTE',
})

// I lettori, uno per livello. ⛔ `CLIENTE` non c'e': il backend non ha ancora la
// funzione, e un lettore che chiama una rotta inesistente darebbe un 404 che si
// legge come «questo cliente non ha saldo».
const LETTORE = {
  [LIVELLO.DOCUMENTO]: getSaldoFattura,
  [LIVELLO.RATA]: getSaldoRata,
}

// Scopo: legge il saldo di UNA cosa, a un livello.
// ⚠️ Il livello si sceglie UNA VOLTA e non e' reattivo: un pannello dei saldi
//    non cambia mestiere mentre e' a video. Se un giorno servisse cambiarlo
//    senza rimontare, si passa `:key="livello"` al componente — cosi' e'
//    esplicito nel chiamante invece che nascosto qui dentro.
// @returns {{saldo, caricato, errore, loading, leggi, azzera, livelloSupportato}}
export function useSaldi(livello) {
  // ⚠️ Si dichiara SUBITO se il livello si sa leggere: un composable che
  //    risponde `null` sia per «non l'ho letto» sia per «questo livello non
  //    esiste ancora» costringe il chiamante a indovinare quale dei due.
  const livelloSupportato = LETTORE[livello] != null

  const { dati: saldo, caricati: caricato, errore, loading, carica, azzera } =
    useLetturaTreStati(
      (id) => LETTORE[livello](id),
      // ⚠️ La forma arriva gia' fatta dal backend (`livello`,
      //    `riferimento_id`, i tre numeri, `has_movimenti`): non si rimappa —
      //    rimappare e' il primo passo per rinominare.
      { estrai: (d) => d },
    )

  async function leggi(riferimentoId) {
    if (!livelloSupportato || riferimentoId == null) {
      azzera()
      return null
    }
    return carica(riferimentoId)
  }

  // ⭐ «Nessuno ha ancora pagato niente» e «il residuo e' zero» sono due fatti
  //    diversi e a video si somigliano. `has_movimenti` li separa, e lo dice il
  //    database: dedurlo da `residuo === totale` sarebbe una seconda regola.
  const senzaMovimenti = computed(
    () => caricato.value && !errore.value && saldo.value?.has_movimenti === false,
  )

  return { saldo, caricato, errore, loading, leggi, azzera, livelloSupportato, senzaMovimenti }
}
