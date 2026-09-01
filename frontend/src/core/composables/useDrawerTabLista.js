// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: scaffolding dei TAB-LISTA dentro un drawer — le liste di
//        sotto-entita' che vivono in un tab del padre (i registri di
//        numerazione e il mapping BA dentro il drawer dell'emittente).
//        Estratto 2026-09-01 (regola del 2, ok Tid) da
//        `EmittenteFiscaleBillingAccountTab`, che era l'unico esemplare.
//
// ⭐ COSA AGGIUNGE A `useListaConfigurabilePage`, e non e' zucchero: il
//    legame col PADRE. Un tab-lista ha un `parentId` che cambia sotto i piedi
//    (si apre un altro emittente senza smontare il drawer), e ogni volta
//    vanno fatte quattro cose nell'ordine giusto: scrivere l'id nello store,
//    azzerare l'offset, azzerare la ricerca — nel form E nello store — e
//    ricaricare. Saltarne una lascia la pagina 3 dell'emittente precedente
//    sopra i dati del nuovo, che e' un difetto che non fallisce: mostra righe
//    vere di un padre sbagliato.
//
// ⛔ E' UNA FACTORY, NON UN OGGETTO CONDIVISO. Ogni chiamata costruisce il
//    proprio stato (`useListaConfigurabilePage` a sua volta costruisce il
//    proprio `useSearchTable`). Esportare un'istanza per de-duplicare
//    sembrerebbe funzionare col primo consumatore e romperebbe il secondo in
//    silenzio: due tab montati insieme si scriverebbero addosso filtri e
//    pagina (`feedback_estrarre_non_condividere_stato`).
//
// ⚠️ IL WATCH E' `immediate`, ED E' IL MOTIVO PER CUI LO PRENDE IN CARICO IL
//    BB. Un tab montato dentro un drawer non passa da `onMounted` quando il
//    padre cambia: il componente resta lo stesso e cambia solo la prop. Chi
//    scriveva il fetch in `onMounted` vedeva i dati del primo padre per
//    sempre.
//
// Uso tipico:
//   const {
//     searchText, onPage, onSort, paginatorProps, tablePage,
//     listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
//     reloadAll,
//   } = useDrawerTabLista(store, {
//     parentId: () => props.emittenteId,
//     parentField: 'emittenteId',
//     fetchExtra: () => store.fetchSummary(),
//     searchTableOptions: { defaultSortField: 'codice' },
//     onNew: () => apriDrawer(null),
//   })

import { watch } from 'vue'
import { useListaConfigurabilePage } from './useListaConfigurabilePage'

export function useDrawerTabLista(
  store,
  {
    // Getter del padre: una funzione, non un valore. Il BB ci mette sopra un
    // `watch`, e un numero letto una volta al setup non cambierebbe mai.
    parentId,
    // Nome della proprieta' dello store che porta l'id del padre
    // (`emittenteId`, `articoloId`, ...). ⚠️ E' una proprieta' dello store,
    // non un filtro: i filtri si azzerano al cambio padre, questa si scrive.
    parentField,
    // Fetch aggiuntiva che il tab deve fare INSIEME alla lista, quando la
    // pagina mostra qualcosa che non sta nella pagina corrente (il summary
    // del mapping BA, da cui dipende un pulsante di testata). Ritorna una
    // Promise o niente.
    fetchExtra = null,
    ...listaOptions
  } = {},
) {
  const lista = useListaConfigurabilePage(store, {
    ...listaOptions,
    // ⚠️ Arrow lazy: `reloadAll` e' dichiarata piu' sotto e viene risolta al
    //    click, non adesso. Senza l'arrow sarebbe una TDZ silenziosa.
    onReload: () => reloadAll(),
  })

  // Scopo: ricarica tutto cio' che il tab mostra, non la sola lista — e' il
  //        comando del pulsante "Ricarica" della PageActionsBar.
  // ⛔ Senza `fetchExtra` un pulsante "Ricarica" ricaricherebbe meta' pagina e
  //    lascerebbe l'altra meta' ferma: e' peggio di non averlo, perche'
  //    l'operatore crede di aver riallineato tutto.
  function reloadAll() {
    lista.reload()
    if (typeof fetchExtra === 'function') fetchExtra()
  }

  watch(
    () => (typeof parentId === 'function' ? parentId() : parentId?.value ?? parentId),
    (id) => {
      if (!id) {
        store.reset()
        return
      }
      if (parentField) store[parentField] = id
      // I tre azzeramenti, e sono tre perche' la ricerca vive in due posti:
      // nello store (quello che parte al backend) e nel campo di testo del
      // caller. Azzerarne uno solo lascia la casella piena sopra risultati
      // non filtrati, o viceversa.
      store.filters.offset = 0
      store.filters.search = ''
      lista.searchText.value = ''
      // Parallelo: la lista e l'extra non dipendono l'una dall'altra.
      const attese = [store.fetchList()]
      if (typeof fetchExtra === 'function') {
        const p = fetchExtra()
        if (p) attese.push(p)
      }
      Promise.all(attese)
    },
    { immediate: true },
  )

  return { ...lista, reloadAll }
}
