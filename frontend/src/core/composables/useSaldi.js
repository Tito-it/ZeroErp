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

// I lettori, uno per livello, ciascuno con cio' che SA fare. ⛔ `CLIENTE` non
// c'e': il backend non ha ancora la funzione, e un lettore che chiama una rotta
// inesistente darebbe un 404 che si legge come «questo cliente non ha saldo».
//
// ⭐ «Prima di se'» (D19-b, 2026-09-17): chi CORREGGE una riga vuole il saldo
//    senza contarsi addosso — altrimenti «in lavorazione» conta proprio i soldi
//    che sta cambiando. Il database lo sa fare sulla rata
//    (`fn_get_saldo_rata(p_scadenza_id, p_escludi_contabile_riga_id)`) e non
//    sul documento (`fn_get_saldo_fattura_contabili` ha un parametro solo —
//    brief D19, P-6): il suo lettore NON inoltra le opzioni, e `esclusione`
//    lo dichiara nella stessa riga, cosi' non c'e' una seconda tabella da
//    tenere allineata alla prima.
// ⛔ Non si «sana» nel frontend sottraendo l'importo della riga: sarebbe la
//    seconda formula del saldo. Si dichiara, e il pannello lo dice.
const LETTORE = {
  [LIVELLO.DOCUMENTO]: { leggi: (id) => getSaldoFattura(id), esclusione: false },
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
