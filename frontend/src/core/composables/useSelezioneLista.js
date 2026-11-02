// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL TELAIO della selezione multipla su una lista PAGINATA — caselle di
//        riga, seleziona-tutto di pagina, prune di ciò che smette di essere
//        selezionabile, e l'oggetto `perLista` che i template consumano.
// Note: sopra `useSelezioneToggle`, che porta il toggle con righe non
//       selezionabili e le tre funzioni di pagina. Qui si aggiunge ciò che quel
//       BB non ha: il PRUNE e la forma del ritorno.
// ------------------------------------------------------------
//
// ⭐ PERCHÉ ESISTE (estratto 2026-09-04, regola del 2, ok Tid). `useSelezioneToggle`
//    copre il toggle, non il giro completo: attorno a lui `useSelezioneLotti` e
//    `useSelezioneCoda` avevano scritto **la stessa trafila** — filtrare le
//    selezionabili della pagina, cablare le quattro funzioni, sorvegliare le
//    righe per togliere dalla selezione ciò che non si può più spuntare,
//    comporre `perLista` con le stesse sette chiavi, esporre `ids`/`azzera`.
//    ⚠️ Misurato prima di estrarre: ~85% in comune, e ciò che divergeva era
//    solo il DOMINIO (quale riga si può spuntare, e perché no).
//
// ⛔ IL PRUNE È LA PARTE CHE NON SI VEDE, ed è la ragione per cui il telaio
//    vale più della somma delle sue righe. Una riga può smettere di essere
//    selezionabile SOTTO LE MANI — un collega la lavora, un giro la fa
//    avanzare, un refresh periodico ricarica la lista. Senza il prune resta
//    spuntata con la casella disabilitata: **non più rimovibile**, contata nel
//    pulsante e ri-sottomessa a ogni atto. Nessun errore, solo un contatore
//    che mente.
//
// ⭐ E IL PRUNE HA DUE MOTIVI, non uno — è la cosa che l'estrazione doveva
//    portarsi dietro senza appianarla:
//      1. la PAGINA rivaluta ciò che mostra. Il predicato si applica
//         all'oggetto FRESCO appena arrivato, non alla copia stantia dentro la
//         selezione: è lì che si legge lo stato cambiato.
//         ⚠️ Guarda SOLO la pagina corrente: le righe delle altre pagine non
//         sono in discussione, e la selezione le attraversa di proposito.
//      2. `escludiOvunque` vale DOVUNQUE, anche su righe che non stiamo
//         guardando. Serve a chi ha uno stato fuori dal dato — le righe dentro
//         un giro asincrono vivo (`useRigheInGiro`): si spunta a pagina 1, si
//         va a pagina 2 e si invia, e col solo motivo 1 quella riga resterebbe
//         spuntata e invisibile.
//
// Config:
// - `righeVisibili`: Ref<row[]> — le righe della PAGINA corrente.
// - `abilitata`: Ref<bool> — c'è il permesso / non siamo in sola lettura.
//   Quando è falsa `perLista` è `null` e la lista non rende nemmeno la colonna
//   delle caselle: nessuna promessa che non si può mantenere.
// - `selezionabile(row) -> bool`: il predicato di dominio. SEDE UNICA — lo
//   usano le caselle, il seleziona-tutto, il guard del toggle e il prune.
// - `motivoNonSelezionabile(row) -> string|undefined`: il tooltip della casella
//   spenta. ⚠️ `undefined` (non stringa vuota) sulle righe spuntabili: un
//   tooltip vuoto comparirebbe comunque, come un rettangolo senza testo.
// - `escludiOvunque(row) -> bool`: motivo 2 del prune (opzionale).
// - `sorveglia`: sorgenti extra da osservare oltre alle righe. Serve quando il
//   motivo 2 NON dipende da una fetch — un `watch` sulle sole righe non
//   scatterebbe, ed è proprio lì che serve.
// - `rowKey`: chiave riga (default `'id'`).
import { computed, ref, watch } from 'vue'
import { useSelezioneToggle } from './useSelezioneToggle'

export function useSelezioneLista({
  righeVisibili,
  abilitata,
  selezionabile,
  motivoNonSelezionabile = () => undefined,
  escludiOvunque = null,
  sorveglia = [],
  rowKey = 'id',
}) {
  const selezione = ref([])

  // Il BB del toggle vuole l'elenco delle selezionabili: qui è quello della
  // PAGINA, coerente col seleziona-tutto di pagina scelto sotto.
  const selezionabiliInPagina = computed(
    () => (righeVisibili.value ?? []).filter(selezionabile),
  )

  const {
    isSelected, toggleRow,
    allInPagina, anyInPagina,
    // ⛔ `toggleAllInPagina` e NON `toggleAll`: la lista è PAGINATA, e il
    //    seleziona-tutto che SOSTITUISCE butterebbe via in silenzio quanto
    //    spuntato nelle altre pagine — l'operatore se ne accorgerebbe solo dal
    //    contatore del pulsante. Il telaio non lascia la scelta al chiamante
    //    proprio perché su cinque liste paginate tre avevano preso quello
    //    sbagliato.
    toggleAllInPagina,
  } = useSelezioneToggle({
    selected: selezione,
    selezionabili: selezionabiliInPagina,
    rowKey,
  })

  watch([righeVisibili, ...sorveglia], () => {
    // Motivo 1 — la pagina rivaluta ciò che mostra (oggetto fresco).
    const nonPiu = new Set(
      (righeVisibili.value ?? [])
        .filter((r) => !selezionabile(r))
        .map((r) => r[rowKey]),
    )
    // Motivo 2 — vale ovunque, anche fuori pagina.
    const filtrata = selezione.value.filter(
      (r) => !nonPiu.has(r[rowKey]) && !(escludiOvunque?.(r) ?? false),
    )
    if (filtrata.length === selezione.value.length) return
    selezione.value = filtrata
  })

  function azzera() {
    selezione.value = []
  }

  // Scopo: tiene spuntate SOLO le chiavi indicate. È il compagno di `azzera`
  //        per gli esiti PARZIALI di un verbo di massa: dopo l'atto si tolgono
  //        le righe riuscite e restano quelle fallite, che sono esattamente
  //        ciò su cui l'operatore deve tornare.
  // ⛔ Senza, le righe riuscite resterebbero spuntate e INVISIBILI: escono
  //    dall'elenco (una riga archiviata è nascosta di default) e quindi la
  //    pagina non le mostra più — il prune, che guarda solo ciò che la pagina
  //    dichiara, non le vedrebbe mai. Il contatore del pulsante continuerebbe a
  //    contarle. `azzera()` lo maschera solo finché il giro riesce del tutto.
  function tieniSolo(chiavi) {
    const tenute = new Set(chiavi)
    const filtrata = selezione.value.filter((r) => tenute.has(r[rowKey]))
    if (filtrata.length === selezione.value.length) return
    selezione.value = filtrata
  }

  return {
    // `null` quando il verbo non è disponibile: vedi `abilitata` sopra.
    perLista: computed(() => (abilitata.value ? {
      isSelezionato: isSelected,
      isSelezionabile: selezionabile,
      motivoNonSelezionabile,
      toggle: toggleRow,
      tuttiInPagina: allInPagina,
      alcuniInPagina: anyInPagina,
      toggleTuttiInPagina: toggleAllInPagina,
    } : null)),
    selezione,
    ids: computed(() => selezione.value.map((r) => r[rowKey])),
    azzera,
    tieniSolo,
  }
}
