// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Una lettura che distingue TRE stati e non due — «c'e'», «e' vuoto»,
//        «non l'ho letto».
// Note: ⛔ E' LA REGOLA, non una comodita'. A video il secondo e il terzo si
//       somigliano — una tendina vuota, una tabella senza righe — ma portano a
//       due conclusioni opposte: «questo cliente non ha rate» e «non so se ne
//       ha» non sono la stessa frase, e la prima, detta al posto della seconda,
//       e' un'AFFERMAZIONE FALSA su cui qualcuno decide.
//
//       ⭐ Estratto il 2026-08-28 alla rilettura critica del cantiere incassi.
//       La ragione per cui vale la pena: lo stesso terzetto era riscritto a mano
//       in QUATTRO punti, e in tre di quei quattro me l'ero dimenticato alla
//       prima stesura — canali di una distinta, rate di una fattura, anteprima
//       di registrazione. Un difetto che si ripete tre volte su quattro non e'
//       una distrazione: e' una cosa che il codice deve dare per costruzione.
//
//       ⚠️ NIENTE `silent`: se la lettura fallisce l'operatore deve saperlo. Il
//       toast lo alza `useApiHandler`; qui si registra solo l'esito.
//       ⚠️ Handler PROPRIO e non quello del chiamante: cosi' una lista che si
//       ricarica non azzera i `campiErrati` del form accanto, che e' il rosso
//       sui campi che l'operatore sta correggendo.
//
//       🔴 GUARD DI VERSIONE (2026-09-14): due `carica` in volo sullo stesso
//       lettore — l'operatore cambia fattura mentre le rate della prima non
//       sono ancora arrivate — possono tornare in ordine inverso, e la
//       risposta STANTIA sovrascriverebbe quella giusta: a video le rate (o il
//       saldo, o i canali) di un ALTRO documento, senza nessun errore. E'
//       esattamente il caso 2 di `useFetchVersion`: ogni `carica` marca la
//       propria chiamata, e al ritorno scrive solo se e' ancora l'ultima.
//       `azzera` invalida quelle in volo — un reset non deve farsi ripopolare
//       da una risposta partita prima.
// ------------------------------------------------------------

import { ref } from 'vue'

import { useApiHandler } from './useApiHandler'
import { useFetchVersion } from './useFetchVersion'

// @param fetcher  (...args) => Promise<response axios>
// @param estrai   trasforma il payload in cio' che serve (default: identita')
// @param vuoto    il valore quando non si e' letto niente (default: `null`;
//                 per un elenco si passa `[]`)
// @returns {{dati, caricati, errore, loading, carica, azzera}}
export function useLetturaTreStati(fetcher, { estrai = (d) => d, vuoto = null } = {}) {
  const { execute, loading } = useApiHandler()
  const versione = useFetchVersion()

  const dati = ref(vuoto)
  // ⭐ I DUE flag insieme dicono i tre stati:
  //      caricati=false            -> non letto
  //      caricati=true, errore     -> tentato e fallito
  //      caricati=true, !errore    -> letto (e allora `dati` e' la verita',
  //                                   vuoto compreso)
  const caricati = ref(false)
  const errore = ref(false)

  function azzera() {
    versione.invalidate()
    dati.value = vuoto
    caricati.value = false
    errore.value = false
  }

  // Scopo: legge, e scrive l'esito SOLO se nel frattempo non e' partita una
  //        lettura piu' nuova (o un `azzera`). Una risposta scartata torna
  //        `null` e non tocca niente: lo stato resta quello della lettura
  //        corrente, che arrivera' per conto suo.
  async function carica(...args) {
    azzera()
    const mia = versione.tag()
    const risposta = await execute(() => fetcher(...args))
    if (!versione.isCurrent(mia)) return null
    // ⛔ `=== null` e non un test di verita': `useApiHandler` risponde `null`
    //    SOLO in caso di errore, e uno `0` o un array vuoto legittimi non
    //    devono leggersi come un fallimento.
    errore.value = risposta === null
    dati.value = risposta === null ? vuoto : estrai(risposta)
    caricati.value = true
    return dati.value
  }

  return { dati, caricati, errore, loading, carica, azzera }
}

// Scopo: l'`estrai` di gran lunga piu' comune — una lista paginata.
export const RISULTATI = (d) => d?.results || []
