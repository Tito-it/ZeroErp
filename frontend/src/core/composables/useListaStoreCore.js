// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//
// ⭐ IL PADRE COMPOSTO (2026-09-27, regola del 2, ok Tid). Il padre di una lista
//    non e' sempre UN id. Puo' essere piu' id nel PATH (i titoli IVA:
//    `/soggetti/{s}/titoli-iva/{t}/…` → `parentField: ['soggettoId',
//    'titoloId']`), e puo' portare con se' l'EMITTENTE del documento — quando
//    la lista a catalogo e' `perimetro_emittente = t` e `multi_emittente = f`,
//    e il backend dichiara `lista_emittente_param` (`emittente_fiscale_id`, o
//    `emittente_soggetto_ruolo_id` per il giornale) → `emittenteParam`.
//    ⛔ Nello stesso giro di lavoro questa forma era nata SEI volte in DUE modi
//    diversi: una chiave-stringa `id|emittente` con la sua `sciogli` (quattro
//    store: titoli IVA, flussi della pratica, revisioni, Storia di fattura e
//    lotto) e un `ref` dell'emittente letto dalla `fetchPage` (documenti
//    generati, versioni di un template). E le due copie avevano gia'
//    semantiche OPPOSTE: la chiave non leggeva finche' mancava l'emittente, il
//    `ref` leggeva lo stesso e partiva senza. Ora e' una forma sola, qui.
// ⛔ LA SEMANTICA E' UNA: SENZA TUTTE LE PARTI DEL PADRE, LA LISTA NON LEGGE.
//    Deciso sul modello, non sui casi: l'emittente di un documento e' NOT NULL
//    — un documento ce l'ha sempre — quindi un emittente assente vuol dire
//    solo «il dettaglio non e' ancora arrivato». Partire senza sarebbe una
//    richiesta che il cancello di perimetro rifiuta (422) a chi vede piu'
//    emittenti; e per l'operatore mono-emittente, che il 422 non lo vedrebbe,
//    sarebbe comunque una lettura fatta PRIMA di sapere di quale documento —
//    niente da guadagnare aspettando il dettaglio che arriva un attimo dopo.
// ⚠️ E L'ATTESA NON E' MUTA: `attesaPadre` e' vero quando una parte c'e' e
//    un'altra manca (documento aperto, emittente non ancora qui), e
//    `DrawerTabLista` la rende come caricamento. Senza, la lista in attesa
//    mostrerebbe la frase del vuoto — «nessuna revisione» — cioe'
//    un'affermazione su righe che nessuno ha letto: la stessa confusione fra
//    «vuota» e «non letta» che `erroreCaricamento` risolve per il fallimento.
//    E se l'attesa non finisce (un chiamante che l'emittente non lo passa) si
//    vede: la lista resta in caricamento, non dice il falso.
// ⭐ PARTI SEPARATE, NON UNA CHIAVE-STRINGA. Il `watch` di `useDrawerTabLista`
//    e' multi-sorgente — confronta ogni parte per valore, e un primitivo
//    cambia solo quando cambia davvero — quindi la ragione della chiave (un
//    oggetto nuovo a ogni lettura rifarebbe la fetch a ogni render) si
//    scioglie senza separatori da comporre e sciogliere in due sedi.
// ⭐ IL PADRE CHE UN EMITTENTE SUO NON CE L'HA (2026-10-21, brief-db-modelli-
//    documento-standard §11 B-6/F-4). Il modello di documento STANDARD non ha
//    emittente (`template_documenti.emittente_fiscale_id` NULL solo li', per
//    CHECK): per lui «emittente assente» non vuol dire «non ancora arrivato»,
//    vuol dire «non esiste». Il chiamante lo dichiara scrivendo nella parte
//    dell'emittente `PADRE_SENZA_EMITTENTE`: la parte conta come presente (la
//    lista legge), e il parametro NON viaggia — il cancello del backend decide
//    allora come per una lista senza emittente suo (la distinta di `catalogo`).
//    ⛔ Non `null` e non `0`: sarebbero indistinguibili dall'attesa, e la
//    lista resterebbe in caricamento per sempre — il difetto che chiude.
// ⚠️ L'emittente NON e' un filtro: non sta in `filterDefaults` (dove «Pulisci
//    filtri» lo toglierebbe e il segno dei filtri lo conterebbe) e non sta in
//    `paramsFiltro`. E' contesto come il padre: si scrive, non si filtra.
import { computed, ref } from 'vue'
import { useContrattoFiltriLista } from './useContrattoFiltriLista'
import { clonaFiltri } from '../utils/clonaFiltri'
import { useListaEmptyStateFetch } from './useListaEmptyStateFetch'
import { USO_MISURA, misuraDefault } from '../misurePagina'
import { paramsOrdinamento, paramsRicerca } from '../utils/listParams'

// La parte «emittente» di un padre che un emittente suo non ce l'ha (vedi la
// testata). Un simbolo: non si confonde con nessun id, e non va mai sul filo.
export const PADRE_SENZA_EMITTENTE = Symbol('PADRE_SENZA_EMITTENTE')

// Params:
//   - fetchPage: (params) => Promise<response axios>. Con `parentField`, la
//       firma diventa (parentId, params) — e' l'endpoint annidato; con piu'
//       parti, (parte1, parte2, …, params), nell'ordine di `parentField`.
//   - parentField: nome della proprieta' che porta l'id del PADRE (`soggettoId`,
//       `fatturaId`), o un ARRAY di nomi quando il path ne ha piu' d'uno
//       (`['soggettoId', 'titoloId']`). ⚠️ E' contesto, non un filtro: al
//       cambio padre i filtri si azzerano, questa si riscrive.
//   - emittenteParam: il nome del parametro di QUERY con cui l'endpoint riceve
//       l'emittente del documento (`lista_emittente_param` della view:
//       `'emittente_fiscale_id'`, `'emittente_soggetto_ruolo_id'`). Lo store
//       espone allora `emittenteId`, una parte del padre come le altre: senza
//       non si legge. ⚠️ Il nome resta `emittenteId` qualunque sia il
//       parametro: che sia la PK o il soggetto-ruolo lo dice `emittenteParam`
//       (`feedback_emittente_pk_vs_soggetto_ruolo`), non il nome della ref.
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
//   - misura: l'USO della lista, da cui esce la misura di PARTENZA
//       (righe per pagina) — `USO_MISURA.PAGINA` di default, che
//       `useSearchTable` tratta come «lista standard» e adatta al viewport
//       (la compatta sotto il tablet). ⭐ Una lista che nasce per un altro uso
//       — `USO_MISURA.COMPATTA` per una lista dentro un dialog, dove l'altezza
//       e' quella di poche righe — resta a quella misura: e' l'eccezione che
//       `useSearchTable` gia' dichiara. Il NUMERO lo dice il catalogo DB
//       (BB `core/misurePagina`), e si legge qui, quando lo store nasce.
//       ⛔ Fino al 2026-09-30 l'opzione era `limit`, un numero preso da
//       `PAGINATION`: scritto nelle opzioni a livello di modulo, oggi sarebbe
//       letto PRIMA che il guard carichi il catalogo.
//       ⚠️ Vale anche per `reset()`: uno store che rinasce alla misura di
//       pagina dopo essere nato compatto cambierebbe passo alla seconda
//       apertura.
export function useListaStoreCore({
  fetchPage,
  parentField = null,
  emittenteParam = null,
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
  misura = USO_MISURA.PAGINA,
  onPayload = null,
  // ⛔ Ritirata il 2026-09-30: si dichiara `misura`. Un'opzione che lo store
  //    scrive e il BB ignora e' un errore silenzioso — qui solleva.
  limit: limitRitirato,
} = {}) {
  if (limitRitirato !== undefined) {
    throw new Error('useListaStoreCore: `limit` e\' ritirata, dichiarare `misura` (USO_MISURA)')
  }
  const limit = misuraDefault(misura)
  // Le parti del padre nel PATH, una ref per nome. `null` = non ancora scelta.
  const nomiPath = parentField == null ? [] : [].concat(parentField)
  const partiPath = nomiPath.map(() => ref(null))
  // L'emittente del documento, quando l'endpoint lo riceve in query.
  const emittenteId = ref(null)
  // Tutte le parti che la lettura aspetta: il path e, se c'e', l'emittente.
  const parti = emittenteParam ? [...partiPath, emittenteId] : partiPath
  // ⚠️ «Vuoto» e' il falsy, come e' sempre stato per il padre singolo: un id
  //    non vale mai 0, e `''` arriva da una prop non ancora popolata.
  const padreCompleto = () => parti.every((p) => !!p.value)
  // Il padre e' a meta': qualcosa c'e', qualcosa manca — la lista ASPETTA
  // (vedi la testata). Con tutto vuoto non aspetta niente: non c'e' un padre.
  // ⚠️ A dire «qualcosa e' aperto» e' il PATH, non l'emittente: un drawer
  //    chiuso passa il documento `null` mentre il dettaglio precedente porta
  //    ancora il suo emittente, e quella non e' un'attesa — e' nessun padre.
  const partiGuida = partiPath.length ? partiPath : parti
  const attesaPadre = computed(
    () => partiGuida.some((p) => !!p.value) && !padreCompleto(),
  )

  // Scopo: i parametri di query che portano l'emittente — `{}` se la lista non
  //        ne ha uno. Esposta perche' lo stesso cancello vale per OGNI metodo
  //        della view (anche la creazione, `templateVersioni.create`): una
  //        seconda sede del nome del parametro divergerebbe da questa.
  function paramsEmittente() {
    return emittenteParam && emittenteId.value && emittenteId.value !== PADRE_SENZA_EMITTENTE
      ? { [emittenteParam]: emittenteId.value }
      : {}
  }

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
  // ⚠️ La ricerca parte dalla soglia DELLA LISTA (`ricercaMinCaratteri`, dalla
  //    configurazione; `RICERCA.MIN_CARATTERI` finche' non arriva): un termine
  //    piu' corto non si manda, e la lista fa cio' che `ricercaCorta` dice.
  //    ⭐ L'export legge la stessa soglia, perche' passa di qui: il file
  //    scaricato cerca come la videata anche su una lista da un carattere.
  // ⚠️ Il confronto e' `!= null`, non un truthy-check: `false` e `0` sono
  //    filtri legittimi («solo i disattivati»), e un `if (f.attivo)` li
  //    tratterebbe come «nessun filtro», mostrando anche gli attivi.
  function paramsFiltro(f = filters.value) {
    // La ricerca con la regola comune (`paramsRicerca`): trim, soglia della lista.
    // ⚠️ `ricercaMinCaratteri` e' dichiarata piu' sotto (dal BB di stato): qui
    //    si legge a CHIAMATA, quando esiste gia' — `paramsFiltro` non gira
    //    durante il setup.
    const params = { ...paramsRicerca(f, { minCaratteri: ricercaMinCaratteri.value }) }
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

  // Scopo: i parametri dell'EXPORT della lista: quelli della videata
  //        (`paramsFiltro`) piu' l'emittente del padre composto.
  // ⛔ L'emittente NON e' un filtro, e `paramsFiltro` non lo porta per
  //    costruzione; ma l'export e' un verbo della lista e passa dallo stesso
  //    cancello di perimetro. Con i soli filtri, chi vede piu' emittenti
  //    leggeva la lista e riceveva 422 all'export (righe dei documenti di
  //    vendita, verifica critica del 2026-09-28). Una sede, perche' il
  //    prossimo padre composto con export non ripeta il difetto.
  function paramsExport() {
    return { ...paramsFiltro(), ...paramsEmittente() }
  }

  const {
    items, totalRecords, loading, hasSearched, sospesa: fetchSospesa,
    // `ricercaFull` (la lista cerca?) e `ricercaMinCaratteri` (da quanti
    // caratteri?): dichiarate dal BB di stato (vedi li').
    ricercaFull, ricercaMinCaratteri,
    fetchList: fetchListBase, svuota,
    // Il termine nuovo cambia la richiesta? Lo chiede `useSearchTable`.
    ricercaCambiaLaRichiesta,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: !startsEmpty,
    ricercaCorta,
    hasActiveFilters: (f) => gateKeys.some((k) => f[k] != null),
    // ⚠️ La paginazione e' l'UNICA cosa che la lista aggiunge ai filtri:
    //    l'export non la manda, il suo limite lo impone il backend.
    buildParams: (f) => ({ ...paramsFiltro(f), limit: f.limit, offset: f.offset }),
    // Le parti del path in testa, nell'ordine di `parentField`; l'emittente in
    // query accanto ai parametri della lista.
    fetchPage: (params) => fetchPage(
      ...partiPath.map((p) => p.value),
      { ...params, ...paramsEmittente() },
    ),
    onPayload,
  })

  // ⛔ Senza padre non si chiama: l'id sta nel PATH dell'endpoint, e una fetch
  //    con `undefined` non tornerebbe una lista vuota — tornerebbe 404. E senza
  //    emittente, quando l'endpoint lo chiede, nemmeno: e' la semantica unica
  //    del padre composto (vedi la testata), non un caso a parte.
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
    if (!padreCompleto()) return false
    try {
      // La pagina che non c'e' piu' la gestisce il BB di stato
      // (`useListaEmptyStateFetch`, `offsetDiRientro`), per ogni lista.
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
    for (const p of parti) p.value = null
    erroreCaricamento.value = false
    filters.value = filtriDiPartenza()
  }

  const esposto = {
    items, totalRecords, loading, hasSearched, filters,
    ricercaFull, ricercaMinCaratteri, ricercaCambiaLaRichiesta,
    // Alzata da chi conosce il motivo (oggi solo il cancello di perimetro
    // emittente, in `useListaConfigurabilePage`): finche' e' true la lista non
    // interroga il backend. Si scrive nei DUE versi, mai una volta sola.
    fetchSospesa,
    erroreCaricamento,
    fetchList, svuota, reset,
    paramsFiltro, paramsExport,
    // Il padre composto: la lista aspetta una parte che manca? E l'emittente
    // in query, per i verbi della stessa view che non sono la lista.
    attesaPadre, paramsEmittente,
    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li'.
    chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri,
  }
  // ⭐ Il padre si espone COL SUO NOME (`soggettoId`, `fatturaId`), non come
  //    `parentId`: e' il nome che il caller scrive in `parentField` di
  //    `useDrawerTabLista` (o come chiave del suo padre composto), ed e'
  //    quello che si legge nei componenti. Ogni parte del path col suo nome;
  //    l'emittente come `emittenteId`.
  nomiPath.forEach((nome, i) => { esposto[nome] = partiPath[i] })
  if (emittenteParam) esposto.emittenteId = emittenteId
  return esposto
}
