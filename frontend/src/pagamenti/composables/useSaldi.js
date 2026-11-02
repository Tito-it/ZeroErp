// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//        backend ha gia' la sua sede vuota per il cliente: quando si accendera'
//        nasce **qui e li'**, e nessun'altra sede cambia.
//
//        ⭐ IL DISLIVELLO E' RIENTRATO (2026-08-29). Fino a ieri la rata dava
//        tre numeri e il documento due: DB-10 e' atterrata il 25/08 e il
//        backend, dal 29/08, la raccoglie — i due livelli rispondono la stessa
//        forma piena.
//        ⛔ Il ramo «non disponibile» RESTA, e non e' un residuo: `null` vuol
//        dire «a questo livello non si sa», che e' diverso da zero, e il primo
//        livello che tornera' a non saperlo (il CLIENTE, finche' somma solo
//        documenti) lo trovera' gia' pronto. ⛔ E non si sana MAI con una somma:
//        sommare per riempire e' inventare un numero su cui qualcuno decide.
// ------------------------------------------------------------

import { computed } from 'vue'

import { getSaldoFattura, getSaldoRata } from '../api/pagamenti'
import { useLetturaTreStati } from '../../core/composables/useLetturaTreStati'

// I tre livelli. ⭐ `CLIENTE` e' dichiarato e **non ancora acceso**: e' il terzo
// livello previsto dalla decisione, e sta qui perche' il giorno in cui nasce si
// veda che era atteso — non che sia stato aggiunto di corsa.
export const LIVELLO = Object.freeze({
  DOCUMENTO: 'DOCUMENTO',
  RATA: 'RATA',
  CLIENTE: 'CLIENTE',
})

// ⭐ I NOMI DEI TRE NUMERI, e stanno qui per la stessa ragione di `LIVELLO`.
//    Il vincolo dice «i numeri si chiamano sempre allo stesso modo ovunque
//    compaiano: un livello puo' non mostrarne uno, ⛔ nessuno puo' RINOMINARLO».
//    Un vincolo sui nomi che vive come stringhe sparse nei template e' un
//    vincolo che nessuno puo' far rispettare: qui e' una lista sola, e chi
//    sbaglia un nome lo scopre dal `validator` invece che da un numero che non
//    compare.
// ⚠️ E' lo stesso terzetto di `CAMPI_SALDO` in `saldi_service.py`: due sedi ci
//    sono perche' sono due processi, ⛔ ma l'ORDINE e i NOMI non si toccano da
//    un lato solo.
export const CAMPI_SALDO = Object.freeze(['residuo', 'in_lavorazione', 'incassato'])

// Scopo: LO SPAZIO di un saldo — quanto ci sta ANCORA, prima di se': il
//        residuo meno cio' che e' gia' digitato su una bozza e non registrato.
//        E' il numero che il guard di capienza confronta (D14-c), quindi e'
//        l'importo che si PROPONE e il predicato «selezionabile» del picker
//        (Q-B, decisione di Tid 2026-09-17: «aperta» = residuo ≠ 0,
//        «selezionabile» e importo proposto = residuo − in lavorazione).
// ⛔ Non e' un quarto numero della base: si CALCOLA dai due che ci sono, e
//    sta qui — non nei tre form che lo usano — perche' una formula scritta in
//    tre posti diverge alla prima regola nuova. Nessuna colonna a DB (Q-B).
// ⚠️ `null` quando manca uno dei due: «non so» non e' zero, e proporre 0 su
//    un saldo non letto inviterebbe a registrare il numero sbagliato.
// ⚠️ Il SEGNO resta: su una nota di credito il residuo e' negativo (P-5) e lo
//    spazio anche — e' «da rimborsare», non «niente da fare». Chi propone un
//    importo guarda `!== 0`, non `> 0`.
// 🔴 La sottrazione si fa in CENTESIMI, non sui float (rilettura del
//    2026-09-17): `100.30 − 100.00` in virgola mobile vale
//    `0.29999999999999716`, e quel numero e' l'importo PROPOSTO — viaggia nel
//    payload cosi' com'e', la colonna `importo` e' `numeric` SENZA scala, e il
//    guard di capienza confronta `abs(importo) > abs(spazio)`: un importo che
//    l'operatore non ha nemmeno toccato veniva rifiutato per capienza. I due
//    numeri arrivano dal database a due decimali: in centesimi la differenza
//    e' esatta.
export function spazioSaldo(saldo) {
  const residuo = saldo?.residuo
  const inLavorazione = saldo?.in_lavorazione
  if (residuo == null || inLavorazione == null) return null
  const centesimi = Math.round(Number(residuo) * 100) - Math.round(Number(inLavorazione) * 100)
  return centesimi / 100
}

// I lettori, uno per livello, ciascuno con cio' che SA fare. ⛔ `CLIENTE` non
// c'e': il backend non ha ancora la funzione, e un lettore che chiama una rotta
// inesistente darebbe un 404 che si legge come «questo cliente non ha saldo».
//
// ⭐ «Prima di se'» (D19-b, 2026-09-17): chi CORREGGE una riga vuole il saldo
//    senza contarsi addosso — altrimenti «in lavorazione» conta proprio i soldi
//    che sta cambiando. Il database lo sa fare sulla rata
//    (`fn_get_saldo_rata(p_scadenza_id, p_escludi_contabile_riga_id)`) e, dal
//    2026-09-18 (P-6 del brief D19), anche sul documento
//    (`fn_get_saldo_fattura(p_fattura_id, p_escludi_contabile_riga_id)`):
//    stesso nome di parametro, stessa domanda — e stessa semantica, dichiarata
//    dal DB nel changeSet: la riga esclusa esce dal dichiarato E, se e' gia'
//    registrata, col suo movimento.
// ⭐ `esclusione` resta accanto al lettore nella STESSA riga: e' la capacita'
//    del livello, e il pannello la legge per DICHIARARE quando un livello non
//    la sa applicare — oggi nessuno dei due vivi, ma il CLIENTE nascera'
//    sommando documenti e una riga non la sapra' escludere. Il ramo e' la
//    risposta a un caso che il modello ammette, non a uno che oggi capita.
// ⛔ Non si «sana» nel frontend sottraendo l'importo della riga: sarebbe la
//    seconda formula del saldo. Si dichiara, e il pannello lo dice.
const LETTORE = {
  [LIVELLO.DOCUMENTO]: { leggi: (id, opzioni) => getSaldoFattura(id, opzioni), esclusione: true },
  [LIVELLO.RATA]: { leggi: (id, opzioni) => getSaldoRata(id, opzioni), esclusione: true },
}

// Scopo: legge il saldo di UNA cosa, a un livello.
// ⚠️ Il livello si sceglie UNA VOLTA e non e' reattivo: un pannello dei saldi
//    non cambia mestiere mentre e' a video. Se un giorno servisse cambiarlo
//    senza rimontare, si passa `:key="livello"` al componente — cosi' e'
//    esplicito nel chiamante invece che nascosto qui dentro.
// @returns {{saldo, caricato, errore, loading, leggi, azzera, livelloSupportato, esclusioneSupportata}}
export function useSaldi(livello) {
  // ⚠️ Si dichiara SUBITO se il livello si sa leggere: un composable che
  //    risponde `null` sia per «non l'ho letto» sia per «questo livello non
  //    esiste ancora» costringe il chiamante a indovinare quale dei due.
  const lettore = LETTORE[livello] ?? null
  const livelloSupportato = lettore != null
  const esclusioneSupportata = lettore?.esclusione === true

  const { dati: saldo, caricati: caricato, errore, loading, carica, azzera } =
    useLetturaTreStati(
      // `carica` inoltra tutti gli argomenti: l'id e le opzioni del lettore.
      (id, opzioni) => lettore.leggi(id, opzioni),
      // ⚠️ La forma arriva gia' fatta dal backend (`livello`,
      //    `riferimento_id`, i tre numeri, `has_movimenti`): non si rimappa —
      //    rimappare e' il primo passo per rinominare.
      { estrai: (d) => d },
    )

  // Scopo: legge il saldo di `riferimentoId`; `escludiRigaId` chiede lo spazio
  //        prima di quella riga, dove il livello lo sa fare.
  async function leggi(riferimentoId, { escludiRigaId = null } = {}) {
    if (!livelloSupportato || riferimentoId == null) {
      azzera()
      return null
    }
    const opzioni = esclusioneSupportata && escludiRigaId != null ? { escludiRigaId } : {}
    return carica(riferimentoId, opzioni)
  }

  // ⭐ «Nessuno ha ancora pagato niente» e «il residuo e' zero» sono due fatti
  //    diversi e a video si somigliano. `has_movimenti` li separa, e lo dice il
  //    database: dedurlo da `residuo === totale` sarebbe una seconda regola.
  const senzaMovimenti = computed(
    () => caricato.value && !errore.value && saldo.value?.has_movimenti === false,
  )

  return {
    saldo, caricato, errore, loading, leggi, azzera,
    livelloSupportato, esclusioneSupportata, senzaMovimenti,
  }
}
