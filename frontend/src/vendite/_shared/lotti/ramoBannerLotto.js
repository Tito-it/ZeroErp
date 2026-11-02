// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA SCELTA DEL RAMO del banner di un lotto fermo — quale frase e con
//        quali numeri — in una funzione PURA: entrano i conteggi del riepilogo
//        e il flag «giro rimediabile», esce la decisione. Il componente fa
//        `t()` su cio' che riceve, e basta.
//        ⭐ Estratta il 2026-09-12 (F2-bis del piano in
//        `brief-db-rilancio-step-non-rivede-le-proprie-commesse` §9.3, deciso
//        con Tid): i rami sono CINQUE su DUE assi (rimediabile × specie del
//        blocco), ed e' il posto in cui un `if` sbagliato non fallisce — mostra
//        la frase sbagliata, e si vede solo quando capita quel caso a video.
//        Con la regola in una funzione senza effetti collaterali ogni ramo ha
//        il suo caso nella spec accanto, come una `fn_check_*` ha il suo pgTAP.
// Note: ⛔ La funzione non conosce `t`, ne' il lotto, ne' lo store: numeri
//        dentro, decisione fuori. ⛔ E' TOTALE sul verdetto: ogni addendo per
//        cui il backend puo' dire `blocks_next_step` (critiche vive, fatture in
//        errore, esiti in errore) ha un ramo — dal 12-09 il banner compare sul
//        VERDETTO e non piu' su `critical_count > 0`, quindi un addendo senza
//        ramo sarebbe un banner senza frase. Il `null` finale e' il caso «il
//        backend blocca per una ragione che non conosco»: il componente lo
//        rende con la frase generica, cosi' un quarto addendo futuro si VEDE
//        invece di sparire.
// ------------------------------------------------------------

import { LOTTO_SCHEDE } from '../../constants'

// Le TRE schede su cui il link del banner puo' atterrare, una per specie:
//   - le critiche si leggono su «Segnalazioni» (filtrata sulle critiche);
//   - un documento il cui ultimo ESITO e' ERRORE senza critica viva NON ha una
//     riga la', e nemmeno fra le fatture: se il pull e' fallito una fattura non
//     e' mai nata. La sua riga sta su «Presi in carico» (`gruppi`, la lista
//     degli esiti), con `ErroreRigaInfo` e il verbo «Togli dal giro»;
//   - una FATTURA in ERRORE nel ponte sta su «Documenti» (`fatture`).
// ⛔ Mandare il ramo degli esiti su Segnalazioni — o su Documenti — aprirebbe
//    un elenco che quella riga non la contiene: il vicolo cieco che le linee
//    guida vietano, e la ragione per cui la scheda e' PARTE della decisione.
// ⚠️ Gli id NON si scrivono qui: sono `LOTTO_SCHEDE`, lo stesso contratto che
//    il template del drawer usa per i suoi `<Tab value>`. Una copia a mano
//    lascerebbe la pagina senza pannello alla prima rinomina, senza errore.

const PREFISSO = 'vendite.lotti.'

// Scopo: un pezzo di frase gia' pronto per `t(chiave, argomenti, plurale)`.
// ⚠️ L'ordine degli argomenti di vue-i18n e' `(chiave, {nomi}, plurale)`: con
//    `(chiave, plurale, {nomi})` il terzo posto viene letto come OPZIONI e ogni
//    segnaposto diverso da `n` sparisce — difetto gia' pagato nel drawer.
//    Qui la forma e' UNA e il componente non la ricompone.
function parte(chiave, argomenti, plurale) {
  return { chiave: PREFISSO + chiave, argomenti, plurale }
}

// Scopo: decide il ramo del banner.
//
// Input (tutti numeri >= 0, `rimediabile` booleano):
//   critiche     — `critical_count`: le segnalazioni critiche VIVE (fatture + lotto)
//   documenti    — `documenti_bloccanti_count`: i documenti con almeno una critica viva
//   presi        — `documenti_presi_in_carico_count`: il denominatore
//   giro         — `critiche_giro_count`: critiche che non appartengono a un documento
//   fattureErrore— `fatture_stato_esecuzione_errore_count`: fatture in ERRORE nel ponte
//   esitiErrore  — `esiti_stato_esecuzione_errore_count`: documenti il cui ULTIMO esito e' ERRORE
//   rimediabile  — `stato_congela_fiscale === false`: il giro puo' ancora essere corretto
//
// Output: `{ parti: [...], scheda }` oppure `null` se nessun conteggio spiega
// il blocco. `parti` sono frasi INTERE da giustapporre (mai frammenti: un
// pezzo senza soggetto non si traduce), `scheda` e' dove porta il link.
//
// ⭐ LA REGOLA DI PRECEDENZA, ed e' la parte che conta: i conteggi NON si
//    sommano. Un documento con una critica viva ha ANCHE l'esito ERRORE (la
//    sovrapposizione e' sconosciuta al client), quindi se ci sono critiche vive
//    parlano QUELLE — sono il segnale piu' fresco — e il ramo degli esiti
//    scatta SOLO a critiche zero, che e' esattamente il caso che D2 esiste per
//    rendere visibile: il lotto che prima usciva COMPLETATO per sottrazione.
export function scegliRamoBanner({
  critiche = 0,
  documenti = 0,
  presi = 0,
  giro = 0,
  fattureErrore = 0,
  esitiErrore = 0,
  rimediabile = false,
} = {}) {
  // ── Giro CONGELATO: le critiche sono STORIA, la frase e' al passato e non
  //    nomina nessun gesto. Un rimedio promesso dall'intestazione e negato
  //    dalla riga e' il vicolo cieco (difetto misurato il 2026-09-08 su tre
  //    lotti annullati ma in ERRORE).
  if (!rimediabile) {
    if (critiche > 0) {
      return { parti: [parte('segnalazioni_giro_chiuso', { n: critiche }, critiche)], scheda: LOTTO_SCHEDE.SEGNALAZIONI }
    }
    if (esitiErrore > 0) {
      return { parti: [parte('segnalazioni_giro_chiuso_esiti', { n: esitiErrore }, esitiErrore)], scheda: LOTTO_SCHEDE.PRESI_IN_CARICO }
    }
    if (fattureErrore > 0) {
      return { parti: [parte('segnalazioni_giro_chiuso_fatture', { n: fattureErrore }, fattureErrore)], scheda: LOTTO_SCHEDE.DOCUMENTI }
    }
    return null
  }

  // ── Giro RIMEDIABILE: le due specie di critica stanno in due frasi, non in
  //    una — un messaggio ha UNA forma plurale, scelta da UN numero.
  if (documenti > 0) {
    const parti = [parte('segnalazioni_bloccanti_documenti', { n: documenti, m: presi }, documenti)]
    if (giro > 0) parti.push(parte('segnalazioni_bloccanti_piu_giro', { k: giro }, giro))
    return { parti, scheda: LOTTO_SCHEDE.SEGNALAZIONI }
  }
  if (giro > 0) {
    return { parti: [parte('segnalazioni_bloccanti_giro', { k: giro }, giro)], scheda: LOTTO_SCHEDE.SEGNALAZIONI }
  }
  // Critiche del canale FATTURA senza documento ne' giro: i tre conteggi sopra
  // descrivono il solo canale LOTTO, e questi numeri non si sommano a quelli.
  if (critiche > 0) {
    return { parti: [parte('segnalazioni_bloccanti', { n: critiche })], scheda: LOTTO_SCHEDE.SEGNALAZIONI }
  }
  // ⭐ D2 (2026-09-12): documenti presi in carico il cui ultimo esito e' ERRORE
  //    e nessuna critica viva — il ramo che prima non esisteva, perche' prima
  //    quel lotto non era nemmeno fermo.
  if (esitiErrore > 0) {
    return { parti: [parte('segnalazioni_bloccanti_esiti', { n: esitiErrore }, esitiErrore)], scheda: LOTTO_SCHEDE.PRESI_IN_CARICO }
  }
  // Fatture in ERRORE nel ponte senza critica viva (guard PRE-1): stessa specie
  // degli esiti, sull'altro canale.
  if (fattureErrore > 0) {
    return { parti: [parte('segnalazioni_bloccanti_fatture', { n: fattureErrore }, fattureErrore)], scheda: LOTTO_SCHEDE.DOCUMENTI }
  }
  return null
}

// Scopo: i conteggi nella forma che `scegliRamoBanner` vuole, letti dal
//        payload di `GET lotti/<id>/segnalazioni/` (`critical_count` in testa,
//        il resto dentro `summary`). E' l'UNICO punto che conosce i nomi
//        dell'envelope: se il backend rinomina un campo, cambia una riga qui.
export function conteggiDaSegnalazioni(segnalazioni, rimediabile) {
  const riepilogo = segnalazioni?.summary ?? {}
  return {
    critiche: segnalazioni?.critical_count ?? 0,
    documenti: riepilogo.documenti_bloccanti_count ?? 0,
    presi: riepilogo.documenti_presi_in_carico_count ?? 0,
    giro: riepilogo.critiche_giro_count ?? 0,
    fattureErrore: riepilogo.fatture_stato_esecuzione_errore_count ?? 0,
    esitiErrore: riepilogo.esiti_stato_esecuzione_errore_count ?? 0,
    rimediabile: rimediabile === true,
  }
}
