// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: quale riga di CODA si può mettere via, e perché no. È tutto ciò che
//        questo file contiene: il giro della selezione (caselle, seleziona-
//        tutto di pagina, prune, forma del ritorno) è del telaio
//        `useSelezioneLista`.
// ------------------------------------------------------------
//
// ⛔ SI SPUNTA SOLO CIÒ CHE SI PUÒ ARCHIVIARE, e la casella spenta è una
//    comodità, NON un presidio: il perimetro vero lo applica il DATABASE, che
//    rifiuta una riga viva col suo trigger. Una riga viva che arrivasse
//    all'API non verrebbe archiviata lo stesso — comparirebbe fra le
//    `falliti` dell'esito parziale, con la sua frase.
//
// ⛔ IL PREDICATO È `rigaCodaViva`, il BB che già esiste, e NON un terzo
//    elenco di stati: «viva» è PENDING o IN_CORSO, la stessa definizione che
//    conta il badge in topbar e che il trigger applica a database. Due letture
//    della stessa coda che non concordano sono già state un difetto.
//
// ⭐ LA SELEZIONE SERVE AL SOLO «ARCHIVIA», ed è una scelta. Il gesto di massa
//    è *ripulire l'elenco*; «Ripristina» è la correzione su una riga che si
//    sta guardando, e resta nel menu di riga. Una selezione che servisse
//    entrambi i verbi ammetterebbe insiemi misti — righe archiviate e non
//    insieme — e il pulsante non saprebbe più cosa promettere.
//
// ⚠️ Il PRUNE del telaio serve qui più che altrove, e per una ragione che le
//    altre liste non hanno: queste due schede si ricaricano DA SOLE ogni 15
//    secondi (`useRefreshPeriodico`). Una riga spuntata può smettere di essere
//    archiviabile sotto le mani — un collega la rimette in coda con
//    «Riaccoda», il drainer la fa ripartire.
import { useI18n } from 'vue-i18n'
import { rigaCodaViva } from '../../core/composables/useQueueCountsPolling'
import { useSelezioneLista } from '../../core/composables/useSelezioneLista'

// `righeVisibili`: le righe della PAGINA corrente (`store.items`).
// `abilitata`: c'è il permesso `code_manage` e non siamo in sola lettura.
export function useSelezioneCoda({ righeVisibili, abilitata }) {
  const { t } = useI18n()

  // Sede UNICA del predicato: il telaio lo gira alle caselle, al
  // seleziona-tutto, al guard del toggle e al prune.
  const selezionabile = (row) => !rigaCodaViva(row?.stato) && row?.archiviato !== true

  // Il motivo sulla casella spenta. `undefined` sulle righe spuntabili.
  function motivoNonSelezionabile(row) {
    if (rigaCodaViva(row?.stato)) return t('strumenti.code.archivia_bloccato_hint')
    if (row?.archiviato === true) return t('strumenti.code.gia_archiviata_hint')
    return undefined
  }

  // ⚠️ Nessun `escludiOvunque` e nessun `sorveglia`: qui lo stato che rende
  //    una riga non archiviabile è NEL DATO (`stato`, `archiviato`), quindi
  //    arriva con la fetch e il motivo 1 del prune basta. È la differenza con
  //    i lotti, dove «è dentro un giro» vive fuori dalla riga.
  return useSelezioneLista({
    righeVisibili,
    abilitata,
    selezionabile,
    motivoNonSelezionabile,
  })
}
