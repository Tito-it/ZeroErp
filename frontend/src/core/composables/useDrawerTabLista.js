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
//     fetchExtra: () => execute(() => store.fetchSummary()), // l'errore lo dice l'extra
//     searchTableOptions: { defaultSortField: 'codice' },
//     onNew: () => apriDrawer(null),
//   })
//
// Uso col PADRE COMPOSTO (documento + emittente; lo store dichiara
// `parentField: 'praticaId'` ed `emittenteParam: 'emittente_fiscale_id'`):
//   useDrawerTabLista(store, {
//     parentId: {
//       praticaId: () => props.praticaId,
//       emittenteId: () => props.emittenteFiscaleId,
//     },
//   })
//   ⛔ Finche' una parte manca la lista NON legge e lo store e' in
//      `attesaPadre` (`DrawerTabLista` la rende come caricamento). Il perche'
//      della semantica sta su `useListaStoreCore`.

import { isRef, watch } from 'vue'
import { useListaConfigurabilePage } from './useListaConfigurabilePage'

export function useDrawerTabLista(
  store,
  {
    // Getter del padre: una funzione, non un valore. Il BB ci mette sopra un
    // `watch`, e un numero letto una volta al setup non cambierebbe mai.
    // ⭐ PADRE COMPOSTO (2026-09-27): un OGGETTO di getter, uno per parte, col
    //    nome della proprieta' dello store come chiave —
    //    `{ praticaId: () => props.praticaId, emittenteId: () => props.emittenteFiscaleId }`
    //    o `{ soggettoId: …, titoloId: … }`. Dove va ogni parte (path o query)
    //    lo sa lo store (`useListaStoreCore`, `parentField`/`emittenteParam`),
    //    non questo BB. Con l'oggetto `parentField` non serve.
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
    // ⭐ Un tab-lista NON e' la lista di rotta: `incorporata` di default, cioe'
    //    non segue la ricerca universale (`?search=`, `ctx.searchTerm`).
    //    Senza, un drawer aperto sotto KeepAlive si ritrovava le righe filtrate
    //    dal termine cercato altrove (il codice del documento: righe vuote),
    //    verifica critica del 2026-09-28. Il caller puo' scavalcarlo. F5 qui
    //    ricarica la lista del tab A VIDEO col drawer in cima
    //    (`useScorciatoie`, dal 2026-10-04).
    searchTableOptions: { incorporata: true, ...listaOptions.searchTableOptions },
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
    if (typeof fetchExtra === 'function') Promise.resolve(fetchExtra()).catch(() => {})
  }

  // Le parti del padre come `[nome, getter]`: una sola per la forma semplice
  // (`parentId` + `parentField`), una per chiave per il padre composto.
  const parti = partiDelPadre(parentId, parentField)
  // ⛔ Una chiave del padre che lo store non ha (`emittenteID`, `documentoId`
  //    su uno store che dichiara `entitaId`) aggiungerebbe una proprieta' nuova
  //    in silenzio: lo store non sarebbe mai completo, e la lista resterebbe
  //    in caricamento per sempre. Si fa rumore in DEV, come `useSearchTable`.
  if (import.meta.env.DEV) {
    for (const [nome] of parti) {
      if (nome && !(nome in store)) {
        console.warn(
          `[useDrawerTabLista] lo store "${store.$id}" non ha la parte del padre "${nome}": ` +
          'la lista non leggera\' mai. Controlla le chiavi di `parentId` / `parentField`.',
        )
      }
    }
  }

  // Scopo: NUOVO PADRE = SI RIPARTE DA CAPO, e in un punto solo: righe
  //        svuotate (invalidando la fetch in volo), filtri, ricerca — nello
  //        store E nella casella — e ordinamento di partenza (`store.reset()`),
  //        poi le parti note scritte nello store.
  // ⛔ Una regola sola per i due rami (padre a meta', padre completo): fino al
  //    2026-09-27 il ramo a meta' azzerava tutto e quello completo solo pagina
  //    e ricerca, quindi l'esito dipendeva da QUANDO arrivava l'emittente — e
  //    le righe del padre precedente restavano a video fino alla risposta, con
  //    i comandi di riga che puntavano al padre nuovo.
  // ⚠️ Resta il passo della pagina (`limit`): e' allineato alla
  //    `pagina_dimensione` della lista una volta sola (`onConfigLoaded`), e
  //    `reset()` lo riporterebbe al default dello store.
  function ripartiDaCapo(valori) {
    const limit = store.filters?.limit
    store.reset()
    if (limit != null) store.filters.limit = limit
    lista.searchText.value = ''
    parti.forEach(([nome], i) => { if (nome && valori[i]) store[nome] = valori[i] })
  }

  // ⭐ WATCH MULTI-SORGENTE: Vue confronta OGNI parte per valore, e la
  //    callback parte solo quando una cambia davvero. E' cio' che permette un
  //    padre composto senza chiave-stringa: un getter che restituisse un
  //    oggetto `{a, b}` avrebbe identita' nuova a ogni rilettura, e la fetch
  //    ripartirebbe a ogni ridisegno senza che niente lo segnali.
  watch(
    parti.map(([, leggi]) => leggi),
    (valori) => {
      const presenti = valori.filter(Boolean).length
      if (presenti === 0) {
        store.reset()
        return
      }
      ripartiDaCapo(valori)
      // ⛔ PADRE A META' = NIENTE LETTURA. Tipicamente il documento e' aperto e
      //    il suo emittente arriva col dettaglio, un attimo dopo. Le parti note
      //    sono scritte: e' cosi' che lo store sa di essere IN ATTESA
      //    (`attesaPadre`) e lo dice, invece di mostrare una lista vuota che
      //    sembra una risposta. La lettura la fa l'arrivo dell'ultima parte,
      //    da questo stesso watch.
      if (presenti < valori.length) return
      // Parallelo: la lista e l'extra non dipendono l'una dall'altra.
      // ⚠️ Il rifiuto dell'extra si assorbe qui: `fetchList` non rifiuta mai
      //    (l'errore diventa `erroreCaricamento`), e un extra che rifiuta in
      //    un `Promise.all` senza `catch` sarebbe una unhandled rejection. A
      //    dire l'errore e' l'extra stesso (toast o stato suo).
      const attese = [store.fetchList()]
      if (typeof fetchExtra === 'function') {
        const p = fetchExtra()
        if (p) attese.push(Promise.resolve(p).catch(() => {}))
      }
      Promise.all(attese)
    },
    { immediate: true },
  )

  return { ...lista, reloadAll }
}

// Scopo: normalizza il padre in `[[nome, getter], …]`.
//   - oggetto semplice (non ref, non funzione) → padre composto, una parte per
//     chiave;
//   - funzione / ref / valore → una parte sola, col nome `parentField` (che
//     puo' mancare: allora non si scrive niente nello store, si legge e basta).
function partiDelPadre(parentId, parentField) {
  if (parentId && typeof parentId === 'object' && !isRef(parentId)) {
    return Object.entries(parentId).map(([nome, g]) => [nome, comeGetter(g)])
  }
  return [[parentField ?? null, comeGetter(parentId)]]
}

function comeGetter(sorgente) {
  if (typeof sorgente === 'function') return sorgente
  if (isRef(sorgente)) return () => sorgente.value
  return () => sorgente
}
