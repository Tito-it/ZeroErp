// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I PARAMETRI D'INGRESSO di una vista (`?open=<id>`, `?tab=`,
//        `?competenza=`…): letti quando arrivano, applicati UNA volta, tolti
//        dalla query. `useIngressoDaQuery({ nomeRotta, gestori })`, con
//        `gestori = { parametro: (valoreGrezzo) => … }`.
// Note: estratto il 2026-11-11 (regola del 2, ok Tid). Il deep-link `?open=`
//       era scritto a mano in `LottiListView` e `ContrattiListView`, ognuno
//       sbagliato in un punto diverso (vedi sotto); il terzo lo chiedevano
//       articoli e promo, per il BERSAGLIO di un errore (brief-db-revisione-
//       dbops, S-BE-1). Lo scheletro e' quello di `useTabDaQuery`, che ora ci
//       si appoggia.
// ------------------------------------------------------------
import { nextTick, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// ── Le tre cose che si dimenticano (e che le copie avevano dimenticato) ─────
//
//  1. ⛔ **Il guard sulla propria rotta.** Sotto KeepAlive i watcher di una
//     vista in cache restano vivi: senza il guard, `ContrattiListView`
//     reagiva a un `?open=` diretto ai LOTTI — apriva il contratto con quel
//     numero e ripuliva una query non sua.
//  2. ⚠️ **Servono `watch` E `onActivated`.** `onActivated` prende l'arrivo da
//     un'altra rotta (la vista in cache non rimonta); il `watch` prende la
//     query che cambia restando sulla pagina. `LottiListView` aveva il solo
//     `onActivated`: dal toast di un errore sui lotti, il «Apri lotto» non
//     apriva niente.
//  3. ⚠️ **La query si pulisce dopo l'uso, in UNA `replace`.** Lasciarla
//     riaprirebbe il pannello a ogni refresh; due `replace` di fila partono
//     dalla stessa query vecchia e la seconda rimette cio' che la prima aveva
//     tolto.
//
// ⭐ Idempotente: `watch` immediato e `onActivated` scattano entrambi al primo
//    ingresso sotto KeepAlive, prima che la `replace` sia arrivata. Gli stessi
//    valori si applicano una volta sola; tolti i parametri, il segno si azzera
//    e lo stesso deep-link, ripetuto, torna a funzionare.
//
// ⛔ La conversione del valore NON sta qui: `?open=` porta un intero o un uuid
//    secondo la destinazione, e lo dice chi la dichiara (`idNellaForma`).
//    Il gestore riceve il valore grezzo della query.

export function useIngressoDaQuery({ nomeRotta, gestori }) {
  const route = useRoute()
  const router = useRouter()
  const nomi = Object.keys(gestori)
  let applicato = null

  function presente(valore) {
    return valore != null && valore !== ''
  }

  function applica() {
    if (route.name !== nomeRotta) return
    const presenti = nomi.filter((n) => presente(route.query[n]))
    if (presenti.length === 0) {
      applicato = null
      return
    }
    const valori = Object.fromEntries(presenti.map((n) => [n, route.query[n]]))
    const segno = JSON.stringify(valori)
    if (applicato === segno) return
    applicato = segno
    const resto = { ...route.query }
    for (const n of presenti) delete resto[n]
    router.replace({ query: resto })
    // Nell'ordine in cui i gestori sono dichiarati (il mese prima del lotto).
    nextTick(() => {
      for (const n of presenti) gestori[n](valori[n])
    })
  }

  watch(() => nomi.map((n) => route.query[n]).join('\u0000'), applica, { immediate: true })
  onActivated(applica)
}
