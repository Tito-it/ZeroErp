// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: lo SCHELETRO di uno store-lista — i filtri nella forma che
//        `useSearchTable` si aspetta, la fetch paginata, il cancello
//        empty-state, la sospensione e il reset. Tutto cio' che serve a una
//        lista, e niente di cio' che serve al CRUD.
//
// Estratto il 2026-09-02 (regola del 2, ok Tid) da `createCrudStore` — che ne
// era l'unico proprietario — nel momento in cui sono nati TRE store-lista
// scritti a mano (`sistemazioniFattura`, `soggettoTitoliIva`,
// `titoliIvaSfondati`). Non potevano usare la factory: due di loro hanno il
// padre nel PATH dell'endpoint (`list(parentId, params)`), forma che
// `createCrudStore` non conosce — e nessuno dei tre e' un CRUD.
//
// ⛔ E LE TRE COPIE AVEVANO GIA' LO STESSO IDENTICO DIFETTO, che e' il modo in
//    cui una duplicazione si fa notare: nessuna esponeva `fetchSospesa`.
//    `useListaConfigurabilePage.onConfigLoaded` la scrive con un guard
//    `'fetchSospesa' in store`, quindi uno store che non la dichiara **non
//    rompe niente** — semplicemente non si sospende mai. Col cancello di
//    perimetro emittente alzato la lista continuava a chiedere pagine che il
//    backend rifiuta con 422, a ogni click, mentre a video c'era il pannello
//    «scegli un emittente». Tre copie, un difetto, zero errori.
//
// ⭐ E' UN COMPOSABLE, NON UNO STORE, e nemmeno un oggetto condiviso: ogni
//    chiamata costruisce il proprio stato. Esportare un'istanza per
//    de-duplicare sembrerebbe funzionare col primo consumatore e romperebbe il
//    secondo in silenzio (`feedback_estrarre_non_condividere_stato`).
//    Lo consumano `createCrudStore` (che ci aggiunge il CRUD),
//    `createListaStore` (che lo impacchetta e basta) e — dal 2026-09-18 — gli
//    store di dominio che hanno TROPPO stato proprio per una factory
//    (`pratiche`, `operatori`, `contratti`, i documenti di vendita…), che lo
//    chiamano direttamente dentro il proprio `defineStore`.
//
// ⭐ IL 2026-09-18 SONO ENTRATI QUI I VENTI STORE SCRITTI A MANO che tenevano
//    una copia del `buildParams` (`search >= 3`, filtri non-null con lo stesso
//    nome, `limit`/`offset`, il blocco dell'ordinamento col suo ripiego). Erano
//    la STESSA forma di questo file, riscritta venti volte con tre differenze
//    che il BB non sapeva ancora esprimere — e che ora sono tre opzioni:
//    `ricercaCorta`, `orderDirDefault`, `paramNames`. Nessuna e' un'invenzione:
//    ognuna e' una divergenza che esisteva gia' in almeno due copie.
import { ref } from 'vue'
import { useContrattoFiltriLista } from './useContrattoFiltriLista'
import { clonaFiltri } from '../utils/clonaFiltri'
import { useListaEmptyStateFetch } from './useListaEmptyStateFetch'
import { PAGINATION } from '../constants'
import { paramsOrdinamento, paramsRicerca } from '../utils/listParams'

// Params:
//   - fetchPage: (params) => Promise<response axios>. Con `parentField`, la
//       firma diventa (parentId, params) — e' l'endpoint annidato.
//   - parentField: nome della proprieta' che porta l'id del PADRE (`soggettoId`,
//       `fatturaId`). ⚠️ E' contesto, non un filtro: al cambio padre i filtri si
//       azzerano, questa si riscrive.
//   - filterDefaults: filtri di dominio con il loro default (no
//       search/limit/offset/order_*, che ci sono sempre).
//   - gateKeys: sottoinsieme di filterDefaults che conta come «ricerca attiva»
//       per il cancello empty-state. Irrilevante con startsEmpty:false.
//   - startsEmpty: true → la lista parte vuota in attesa di una ricerca;
//       false → parte piena (always-fetch).
//   - ricercaCorta: cosa fa una lista che parte PIENA quando nella casella ci
//       sono 1-2 caratteri — `'fetch'` (default: si fetcha comunque, la lista
//       resta piena), `'svuota'`, `'ignora'`. E' il parametro omonimo di
//       `useListaEmptyStateFetch`, passato tal quale: le tre UX convivono nel
//       prodotto e la scelta e' dello store, non del BB.
//   - orderBy / orderDir: ordinamento di partenza.
//   - orderDirDefault: il RIPIEGO del verso quando `order_by` c'e' e
//       `order_dir` no (`paramsOrdinamento`). Default `'asc'`, che e' quello
//       che questo BB ha sempre avuto. ⛔ E' un parametro e non si deriva da
//       `orderDir`: nelle venti copie il ripiego NON coincideva sempre col
//       verso di apertura (`contratti` e `conversioniUom` aprono `desc` e
//       ripiegano `asc`), e il ramo oggi e' dormiente — `useSearchTable.onSort`
//       scrive sempre i due campi insieme — quindi appianarlo sarebbe stato
//       invisibile E avrebbe cambiato il verso di una lista il giorno in cui
//       il ramo si accendesse. Un'estrazione appiana la duplicazione, non le
//       differenze.
//   - paramNames: il NOME SUL FILO di un filtro, quando diverge da quello nello
//       store — `{ data_a: 'data_al' }`. Serve ai due documenti di vendita il
//       cui endpoint chiama le date a modo suo (offerte `validita_dal_min/max`,
//       preventivi `data_al`) mentre nello store devono restare `data_da`/
//       `data_a`, perche' sono i nomi che `useSearchTable` azzera sul deep-link
//       e che `useStoreFilterBindings` lega ai DatePicker. ⚠️ E' una mappa di
//       nomi, non un hook: la FORMA del parametro resta quella del BB.
//   - onPayload(payload): l'hook per i campi EXTRA che l'endpoint mette
//       ACCANTO a `results`/`count` (`scartate_count`, un catalogo, una
//       matrice). E' la STESSA opzione, con lo stesso nome e lo stesso
//       contratto, di `useListaEmptyStateFetch` — passata tal quale, dopo il
//       guard di versione: le risposte scartate non la vedono. Omessa =
//       comportamento invariato (2026-09-19, regola del 2: le righe della
//       distinta ne avevano bisogno e lo store era sul core, dove l'hook non
//       arrivava).
//   - limit: righe per pagina di PARTENZA. Default `PAGINATION.DEFAULT_ROWS`
//       (25), che `useSearchTable` tratta come «lista standard» e adatta al
//       viewport (10 sotto il tablet). ⭐ Una lista che nasce a un altro
//       numero — `PAGINATION.COMPACT_ROWS` per una lista dentro un dialog,
//       dove l'altezza e' quella di dieci righe — resta a quel numero: e'
//       l'eccezione che `useSearchTable` gia' dichiara («le liste che nascono
//       a 10 restano eccezioni»), e prima di questa opzione si poteva
//       scrivere solo negli store a mano (`listini`, `pratiche`).
//       ⚠️ Vale anche per `reset()`: uno store che rinasce a 25 dopo essere
//       nato a 10 cambierebbe passo alla seconda apertura.
export function useListaStoreCore({
  fetchPage,
  parentField = null,
  filterDefaults = {},
  // ⭐ I VALORI CHE NON RESTRINGONO, quando non sono `null` (2026-09-23).
  //    Il segno dei filtri attivi conta un filtro se ha un valore; per quasi
  //    tutti «tutto» e' `null` e basta cosi'. Non per quelli il cui «tutto»
  //    deve viaggiare sul filo: `solo_ultima_revisione: false` (il BE e'
  //    `default=True`, quindi l'assenza significa il contrario) e
  //    `ambito: 'tutti'` delle code. ⛔ Senza, accendere «mostra storico» —
  //    cioe' ALLARGARE la lista — fa SALIRE il numero. Perche' si dichiara qui
  //    e non si indovina: e' conoscenza del filtro, come `paramNames`.
  filtriNeutri: filtriNeutriOpz = {},
  gateKeys = [],
  startsEmpty = true,
  ricercaCorta = 'fetch',
  orderBy = null,
  orderDir = 'asc',
  orderDirDefault = 'asc',
  paramNames = {},
  limit = PAGINATION.DEFAULT_ROWS,
  onPayload = null,
} = {}) {
  // L'id del padre, quando la lista ne ha uno. `null` = nessun padre scelto.
  const parentId = ref(null)

  // ⛔ IL TERZO CASO. Una lista vuota e una lista NON LETTA si assomigliano —
  //    `items` e' `[]` in entrambi i casi, e `hasSearched` resta falso — ma
  //    dicono cose opposte: «qui non c'e' niente» e' un'affermazione su cui
  //    qualcuno decide, «non sono riuscito a leggere» dice solo che non si sa.
  //    Sta nel BB e non nel singolo store perche' la distinzione non e' di
  //    dominio: vale per ogni lista, e finora nessuna delle tre poteva farla.
  const erroreCaricamento = ref(false)

  // Scopo: i filtri di partenza — una funzione e non un letterale perche' li
  //        scrive sia la nascita sia `reset()`, e due letterali divergono.
  // ⛔ `clonaFiltri` e non uno spread, ed e' la stessa ragione che sta su
  //    `useContrattoFiltriLista`: con un default ad ARRAY lo spread mette nei
  //    filtri vivi LO STESSO array del letterale dello store, e il primo widget
  //    che ci scrive dentro (`push`) muta il default — da li' in poi il segno
  //    legge «sempre al default» su una lista ristretta a mano, senza nessun
  //    errore. Il perche' per intero sta su `core/utils/clonaFiltri`.
  function filtriDiPartenza() {
    return {
      // ⚠️ `search` c'e' SEMPRE, anche sulle liste che non cercano: fa parte del
      //    contratto di `useSearchTable`, che la scrive sul deep-link `?search=`.
      //    Dichiararla e' meglio che farla nascere per assegnazione.
      search: '',
      ...clonaFiltri(filterDefaults),
      limit,
      offset: 0,
      order_by: orderBy,
      order_dir: orderDir,
    }
  }

  const filters = ref(filtriDiPartenza())

  // ⭐ CHI SONO I FILTRI DI QUESTA LISTA, e quali valori hanno per nascita. Le
  //    due cose esistevano gia' qui dentro e non uscivano: le legge il segno
  //    dei filtri attivi di `FiltriLista` (`segnoFiltri`, D4 di Tid
  //    2026-09-22), che senza di esse dovrebbe indovinarle — e indovinare
  //    vuol dire contare `limit`/`offset`/l'ordinamento come se fossero
  //    filtri, oppure tenere nel frontend un secondo elenco che diverge al
  //    primo filtro aggiunto.
  // ⛔ `search` NON c'e', ed e' una decisione (D2): la ricerca non e' un
  //    filtro — e' il gesto principale della lista, e gli altri la
  //    restringono. Resta sempre a video anche in modalita' compatta.
  // ⭐ LE TRE RIGHE SONO USCITE DI QUI IL 2026-09-23 (regola del 2, ok Tid):
  //    quattordici liste hanno lo store scritto a mano e devono poter offrire
  //    lo STESSO contratto senza cedere il proprio `buildParams`. Il core lo
  //    CONSUMA, non lo ricopia — una seconda copia di «chi sono i filtri»
  //    diverge al primo filtro aggiunto da una parte sola.
  // ⚠️ `fetchList` e' una dichiarazione di funzione (issata), quindi qui e' gia'
  //    definita anche se compare piu' sotto.
  const { chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri } = useContrattoFiltriLista({
    filters, filterDefaults, filtriNeutri: filtriNeutriOpz, fetchList,
  })

  // Scopo: i parametri che decidono QUALI righe — ricerca, filtri di dominio,
  //        ordinamento — senza la paginazione. E' la sede unica per la fetch
  //        della lista E per il suo export: un export che si ricostruisce i
  //        filtri a mano esporta un insieme DIVERSO da quello a video appena
  //        se ne aggiunge uno, e nessuno se ne accorge finche' qualcuno non
  //        confronta il file con la schermata (la lezione di
  //        `famiglieDocumento`, che l'aveva gia' scritta nel proprio store).
  // ⚠️ La ricerca parte da `RICERCA.MIN_CARATTERI`, ed e' la policy di progetto
  //    (`api.md` §Ricerca): un termine piu' corto non si manda, e la lista
  //    fa cio' che `ricercaCorta` dice.
  // ⚠️ Il confronto e' `!= null`, non un truthy-check: `false` e `0` sono
  //    filtri legittimi («solo i disattivati»), e un `if (f.attivo)` li
  //    tratterebbe come «nessun filtro», mostrando anche gli attivi.
  function paramsFiltro(f = filters.value) {
    // La ricerca con la regola comune (`paramsRicerca`): trim, soglia unica.
    const params = { ...paramsRicerca(f) }
    // Ogni filtro di dominio valorizzato, anche quelli non-gate (es.
    // `attivo: true`: default valorizzato, inviato sempre). Sul filo va col
    // nome che l'endpoint si aspetta (`paramNames`), che di norma e' lo stesso.
    for (const k of Object.keys(filterDefaults)) {
      if (f[k] != null) params[paramNames[k] ?? k] = f[k]
    }
    // ⚠️ L'ordinamento si manda solo se c'e', ed e' la STESSA forma che
    //    l'export della lista usa (`paramsOrdinamento`, dal 2026-09-18): il
    //    file segue la videata perche' i due chiedono l'ordine allo stesso
    //    modo, non perche' due copie coincidono.
    return { ...params, ...paramsOrdinamento(f, { orderDirDefault }) }
  }

  const {
    items, totalRecords, loading, hasSearched, sospesa: fetchSospesa,
    // `ricercaFull`: la lista cerca? Dichiarata dal BB di stato (vedi li').
    ricercaFull,
    fetchList: fetchListBase, svuota,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: !startsEmpty,
    ricercaCorta,
    hasActiveFilters: (f) => gateKeys.some((k) => f[k] != null),
    // ⚠️ La paginazione e' l'UNICA cosa che la lista aggiunge ai filtri:
    //    l'export non la manda, il suo limite lo impone il backend.
    buildParams: (f) => ({ ...paramsFiltro(f), limit: f.limit, offset: f.offset }),
    fetchPage: (params) => (
      parentField ? fetchPage(parentId.value, params) : fetchPage(params)
    ),
    onPayload,
  })

  // ⛔ Senza padre non si chiama: l'id sta nel PATH dell'endpoint, e una fetch
  //    con `undefined` non tornerebbe una lista vuota — tornerebbe 404.
  // ⚠️ L'esito di `fetchListBase` e' `false` anche quando la risposta viene
  //    SCARTATA perche' stantia, e li' NON c'e' nessun errore da dichiarare:
  //    una fetch piu' recente e' in volo e sara' lei a scrivere lo stato. Per
  //    questo l'errore si accende solo su `catch`.
  // ⛔ E il rifiuto NON si ri-solleva: qui e' gia' gestito — diventa
  //    `erroreCaricamento`, che il caller rende come avviso. Ri-sollevarlo dopo
  //    averlo trattato lo farebbe atterrare in un `Promise.all` senza `catch`
  //    (`useDrawerTabLista`), cioe' una unhandled rejection che non dice a
  //    nessuno niente in piu' di quello che l'avviso dice gia'.
  async function fetchList(opzioni) {
    if (parentField && !parentId.value) return false
    try {
      const esito = await fetchListBase(opzioni)
      erroreCaricamento.value = false
      return esito
    } catch {
      erroreCaricamento.value = true
      return false
    }
  }

  // Scopo: riporta la lista allo stato di partenza — usata dai BB di drawer
  //        quando il padre sparisce (`useDrawerTabLista`).
  // ⚠️ `svuota` del BB e non un clear a mano: invalida anche le fetch in volo,
  //    cosi' la risposta del padre precedente non ripopola la lista.
  // ⚠️ E si azzerano TUTTI i filtri, non solo l'offset: un reset parziale e' il
  //    posto dove il primo filtro aggiunto domani sopravvive al cambio di
  //    padre, mostrando righe filtrate come se fossero tutte.
  function reset() {
    svuota()
    parentId.value = null
    erroreCaricamento.value = false
    filters.value = filtriDiPartenza()
  }

  const esposto = {
    items, totalRecords, loading, hasSearched, filters,
    ricercaFull,
    // Alzata da chi conosce il motivo (oggi solo il cancello di perimetro
    // emittente, in `useListaConfigurabilePage`): finche' e' true la lista non
    // interroga il backend. Si scrive nei DUE versi, mai una volta sola.
    fetchSospesa,
    erroreCaricamento,
    fetchList, svuota, reset,
    paramsFiltro,
    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li'.
    chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri,
  }
  // ⭐ Il padre si espone COL SUO NOME (`soggettoId`, `fatturaId`), non come
  //    `parentId`: e' il nome che il caller scrive in `parentField` di
  //    `useDrawerTabLista`, ed e' quello che si legge nei componenti.
  if (parentField) esposto[parentField] = parentId
  return esposto
}
