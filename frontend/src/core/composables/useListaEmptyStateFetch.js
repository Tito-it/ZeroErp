// Building block: stato lista + guardia empty-state per le SearchTable che
// partono vuote (frontend-standards "Empty state — liste che partono vuote").
//
// Estratto 2026-06-03 (regola del 2): la guardia empty-state — search < 3
// caratteri ignorata, primo caricamento senza filtri resta vuoto, search
// svuotata senza filtri torna a stato vuoto — era duplicata bit-per-bit nei
// `fetchList` di 3 store vendite (offerte, preventivi, ordini). È la parte
// fragile/error-prone (i 3 reset di items/totalRecords/hasSearched vanno tenuti
// in sync); la centralizziamo qui.
//
// Ciò che resta al caller, perché DIVERGE legittimamente fra domini, sono i 3
// callback iniettati:
//  - `hasActiveFilters(f)` → bool: quali filtri contano come "ricerca attiva"
//    (stato/utility/date/listino/...). `data_da` col default standard di solito conta,
//    così la lista si popola al mount.
//  - `buildParams(f, searchTerm, ricerca)` → object: la mappatura
//    filtri→query params, che differisce per dominio (nomi filtri diversi;
//    la finestra e' `limit`/`offset` per tutti dal 2026-10-21). Riceve `searchTerm` già trimmato e `ricerca` =
//    `{ minCaratteri }`, la soglia DELLA LISTA: il caller la passa a
//    `paramsRicerca(f, ricerca)`, che manda il termine solo da lì in su.
//  - `fetchPage(params)` → Promise di una response axios con envelope standard
//    `{ data: { data: { results, count } } }` (paginated_envelope BE).
//  - `alwaysFetch` (default false): se true salta i guard empty-state e carica
//    SEMPRE (liste che partono piene: admin, geo). Il search sotto la soglia
//    della lista resta ignorato da `buildParams`, quindi la lista resta piena mentre si digita
//    (no flash vuoto). Usato dalla factory `createCrudStore` con startsEmpty:false.
//
// Ritorna lo stato reattivo (items/totalRecords/loading/hasSearched/sospesa/
// ricercaFull/ricercaMinCaratteri) + fetchList + `ricercaCambiaLaRichiesta`
// (vedi li').
// Lo store espone questi ref nel proprio `return` insieme a `filters` e alle
// azioni CRUD.

// ⚠️ GUARD DI VERSIONE (2026-08-10) — `fetchList` puo' essere in volo PIU' VOLTE
// contemporaneamente, e le risposte non tornano nell'ordine in cui sono partite.
// Senza guard vince l'ULTIMA ARRIVATA, non l'ultima chiesta.
//
// Difetto reale, segnalato da Tid sui preventivi: cerchi `0000192`, compare la
// riga giusta, e un istante dopo la lista si ripopola con TUTTO. Alla seconda
// ricerca funziona. La spiegazione del «solo la prima volta» e' che al primo
// ingresso c'e' una fetch concorrente che dopo non c'e' piu': il caricamento di
// `onMounted` (che parte davvero, perche' il default `data_da` conta come filtro
// attivo e supera la guardia empty-state) — piu', quando presenti, il riallineo
// di `onConfigLoaded` e `useTabFreshness`. La fetch senza search e' la piu'
// lenta perche' non filtra nulla: parte prima e atterra dopo.
//
// Non e' cosmetico: la lista mostra un risultato che NON corrisponde a quello
// che si legge nella casella di ricerca. Si riusa `useFetchVersion`, la stessa
// primitiva di `usePagedDashFetch` — anche `loading` si spegne solo sulla fetch
// corrente, altrimenti una risposta scartata toglierebbe lo spinner a una
// chiamata ancora in corso.
import { ref } from 'vue'
import { useFetchVersion } from './useFetchVersion'
import { paramsRicerca, termineCorto, termineRicerca } from '../utils/listParams'

// «Nessuna richiesta nota»: prima della prima fetch, dopo `svuota()`, dopo un
// errore. Un `Symbol` e non `undefined`, che e' gia' un valore legittimo
// («richiesta partita senza `search`»).
const NESSUNA_RICHIESTA = Symbol('nessuna-richiesta')

// `ricercaCorta` (2026-08-10, migrazione delle 19 store che avevano il ciclo a
// mano): cosa fa una lista `alwaysFetch` quando nel campo search ci sono 1-2
// caratteri. Le TRE UX convivono nel prodotto e l'opzione esiste per migrare
// gli store SENZA CAMBIARE cio' che l'operatore vede:
//  - 'fetch' (default): si fetcha comunque; `buildParams` ignora il termine
//    corto, quindi la lista resta piena mentre si digita («intanto ti lascio
//    quello che c'era»). E' il comportamento della factory `createCrudStore`.
//  - 'svuota': la ricerca corta SVUOTA la lista («quello che vedi non c'entra
//    piu' con quello che leggi nella casella»). Usato da catalogo (unita' di
//    misura, tipi UoM), listini e template documenti.
//  - 'ignora': no-op totale — niente richiesta, la lista resta com'e'. Usato
//    dove la lista alimenta anche una selezione a lato (pratiche: svuotarla
//    annullerebbe `selectedItem` e i guard che ne derivano) o dove il refetch
//    del default sarebbe solo traffico inutile (righe listino).
// Ignorato quando `alwaysFetch` e' false: li' la guardia empty-state fa gia'
// questo e altro.
// `onPayload(payload)` (2026-09-03, regola del 2 — ok Tid): l'hook per i campi
// EXTRA che l'endpoint mette ACCANTO a `results`/`count`. Non e' un'invenzione:
// e' la stessa opzione, con lo stesso nome e lo stesso contratto, che il BB
// gemello `usePagedDashFetch` ha gia' — i due erano allineati su tutto tranne
// questo. Omesso = comportamento invariato, e i 19 store esistenti non cambiano
// di una riga.
//
// ⛔ Invocato SOLO dopo il guard di versione, ed e' l'unica ragione per cui
//    l'hook deve stare QUI e non nel `fetchPage` del caller: tappare la promise
//    la' fuori applicherebbe quei campi anche alle risposte SCARTATE, e il
//    riquadro di totali finirebbe a raccontare un contesto diverso dalla lista
//    sopra di se'. E' la stessa avvertenza scritta nel gemello, e nasce dallo
//    stesso difetto dei preventivi che ha motivato il guard.
// ⚠️ Primo consumatore: il registro lotti, che riceve accanto alla lista la
//    ripartizione per stato dei pulsanti-filtro. Chip e righe vengono dalla
//    STESSA risposta e non possono divergere.
// ⚠️ `svuota()` NON invoca l'hook, esattamente come il `reset()` del gemello:
//    il BB non sa cosa il caller abbia fatto del payload, quindi lo stato extra
//    lo azzera chi l'ha scritto. Allineamento deliberato — due BB gemelli con
//    lo stesso nome di opzione e due contratti diversi sarebbero peggio di due
//    nomi diversi.
export function useListaEmptyStateFetch({ filters, hasActiveFilters = () => false, buildParams, fetchPage, alwaysFetch = false, ricercaCorta = 'fetch', onPayload = null }) {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)
  // Sospensione della lista: quando e' alzata, `fetchList` non parte e basta.
  // Nasce per il cancello di perimetro emittente (P-2b) — con il cancello su,
  // il backend rifiutera' OGNI richiesta di quella lista con 422 finche'
  // l'emittente non e' scelto, e continuare a chiederglielo a ogni tasto
  // premuto e' solo traffico.
  //
  // ⚠️ Vive QUI e non nel composable di pagina perche' qui c'e' UN punto: gli
  //    ingressi alla fetch sono sei (debounce della ricerca, page, sort, F5,
  //    reload, refetch di `onActivated`) e presidiarli uno per uno sarebbe una
  //    lista di posti da ricordare — il settimo nascerebbe scoperto.
  // ⚠️ NON copre la primissima chiamata delle liste `alwaysFetch`: parte
  //    insieme alla config, cioe' prima che si sappia se il cancello e' su.
  //    Quella resta una richiesta rifiutata, ed e' l'unica.
  const sospesa = ref(false)
  // ⭐ LA LISTA CERCA? Lo dice la configurazione risolta dal backend
  //    (`ricerca_full`: almeno una colonna accesa a catalogo per questo
  //    operatore — brief-be-ricerca-full-liste-residue §7-bis). La scrive
  //    `useListaConfigurabilePage.onConfigLoaded`, la legge `FiltriLista` per
  //    mostrare o no la casella: una casella su una lista senza colonne accese
  //    non troverebbe niente, per costruzione (il BB del backend mette `FALSE`).
  // ⚠️ `null` = «non si sa ancora» (configurazione non arrivata, o superficie
  //    senza catalogo): la casella resta. Solo `false` la toglie.
  // ⛔ NON e' un filtro e non sta in `filters`: `svuota()` non la tocca, perche'
  //    e' un fatto della lista, non una scelta dell'operatore.
  // ⭐ Vive QUI dal 2026-09-24 (regola del 2, ok Tid): la stessa dichiarazione,
  //    con lo stesso commento, stava in `useListaStoreCore` e nei quattro store
  //    di pagamenti scritti a mano. Qui la ricevono tutti gli store della lista,
  //    compresi quelli che nasceranno scritti a mano.
  const ricercaFull = ref(null)
  // ⭐ DA QUANTI CARATTERI la lista cerca: un fatto della LISTA, non di chi la
  //    chiama (Tid, 2026-09-24 — brief-db-be-fe-ricerca-soglia-per-lista): una
  //    tabella di configurazione a codici corti cerca da uno («KG», «FT»), un
  //    archivio che cresce da tre. Lo dice la configurazione risolta
  //    (`ricerca_min_caratteri`, la stessa colonna con cui il BB del backend
  //    decide se filtrare) e la scrive `useListaConfigurabilePage.onConfigLoaded`.
  // ⚠️ `null` = «non si sa ancora»: vale `RICERCA.MIN_CARATTERI`
  //    (`listParams.termineCorto`). Come `ricercaFull`, non e' un filtro e
  //    `svuota()` non la tocca.
  // ⛔ La leggono SOLO `termineCorto`/`paramsRicerca`, via `fetchList` qui
  //    sotto: e' cosi' che guardia empty-state e parametro `search` non possono
  //    usare due soglie diverse. Fino al 2026-09-26 il backend cercava da uno e
  //    il frontend mandava da tre: «KG» non arrivava mai.
  const ricercaMinCaratteri = ref(null)
  const fv = useFetchVersion()
  // Il parametro `search` dell'ultima richiesta PARTITA (non arrivata: una
  // richiesta in volo per «abc» conta gia', o cancellando fino ad «ab» la
  // lista filtrata atterrerebbe sotto una casella che non cerca piu').
  let ricercaInviata = NESSUNA_RICHIESTA

  // Scopo: riporta la lista allo stato vuoto E scarta le risposte in volo.
  // L'invalidate e' la parte che non si puo' omettere: senza, una fetch gia'
  // partita atterra con tag ancora corrente e ripopola la lista appena
  // svuotata (lo stesso difetto dei preventivi, rientrato dai rami di
  // guardia). Lo spinner va spento qui: la fetch invalidata non lo spegne
  // piu', perche' il suo `finally` e' gated su `isCurrent`.
  // Esposto ai caller per i reset di contesto esterni al BB (es. pratiche
  // senza emittente corrente).
  function svuota() {
    fv.invalidate()
    ricercaInviata = NESSUNA_RICHIESTA
    items.value = []
    totalRecords.value = 0
    hasSearched.value = false
    loading.value = false
  }

  // `silent: true` → la lista si aggiorna SENZA accendere `loading`. Serve ai
  // refresh PERIODICI (le due schede delle code): la maschera di caricamento
  // del DataTable che lampeggia ogni pochi secondi su una lista che l'operatore
  // sta leggendo è peggio del dato stantio che va a correggere.
  // ⚠️ Cambia SOLO lo spinner: il guard anti-race (`fv.tag`/`isCurrent`) resta
  // identico, altrimenti un refresh silenzioso potrebbe sovrascrivere una
  // fetch più recente — che è il difetto che quel guard esiste per impedire.
  // ⚠️ Chi passa `fetchList` direttamente come handler di evento riceve
  // l'oggetto Event come primo argomento: `silent` risulta `undefined`, cioè
  // falsy, e il comportamento resta quello di sempre.
  async function fetchList({ silent = false } = {}) {
    let esito = await leggiPagina({ silent })
    const rientro = esito ? offsetDiRientro() : null
    if (rientro !== null) {
      filters.value.offset = rientro
      esito = await leggiPagina({ silent })
    }
    return esito
  }

  // Scopo: la pagina chiesta non esiste piu' (la lista si e' accorciata sotto
  //        l'operatore: ha eliminato l'unica riga dell'ultima pagina, o l'ha
  //        fatto un altro, o una coda si e' svuotata). Ritorna l'offset da cui
  //        rileggere, o `null` se la pagina a video e' buona.
  // ⭐ Si torna all'ULTIMA pagina reale, non alla prima: chi ha appena
  //    cancellato in fondo alla lista vuole restare in fondo. Il totale e'
  //    vero anche oltre la fine: lo garantisce il backend
  //    (`fetch_paged_with_total`, dal 2026-09-28).
  // ⚠️ Totale 0 con offset > 0: si rilegge da capo, che e' comunque la
  //    risposta giusta (la lista e' davvero vuota, o l'endpoint non sa contare
  //    oltre la fine).
  // ⚠️ Legge `limit`/`offset` dei FILTRI: e' il contratto di chi usa questo BB,
  //    ed e' la stessa lingua del backend (un dialetto solo dal 2026-10-21).
  //    Una lista senza `offset` non arretra.
  // ⛔ Una rilettura sola, mai un ciclo: la seconda risposta si scrive com'e'.
  function offsetDiRientro() {
    const { offset, limit } = filters.value
    if (!(offset > 0) || items.value.length > 0) return null
    const totale = totalRecords.value
    if (!(totale > 0) || !(limit > 0)) return 0
    const ultima = Math.floor((totale - 1) / limit) * limit
    return ultima < offset ? ultima : null
  }

  async function leggiPagina({ silent = false } = {}) {
    if (sospesa.value) return false
    const f = filters.value
    const searchTerm = termineRicerca(f)
    // Soglia del termine in una sede sola (`listParams.termineCorto`), la
    // stessa con cui `paramsRicerca` decide se mandarlo: quella della lista.
    const ricerca = { minCaratteri: ricercaMinCaratteri.value }
    const corta = termineCorto(searchTerm, ricerca)

    // Liste che partono piene: comportamento della ricerca corta secondo
    // `ricercaCorta` (vedi sopra). Il default 'fetch' prosegue e basta.
    if (alwaysFetch && corta) {
      if (ricercaCorta === 'svuota') {
        svuota()
        return false
      }
      if (ricercaCorta === 'ignora') return false
    }

    // Guard empty-state: SOLO in modo "starts-empty" (default). In `alwaysFetch`
    // (liste che partono piene) si salta tutto e si carica sempre.
    if (!alwaysFetch) {
      const hasFilters = hasActiveFilters(f)
      // Search sotto la soglia della lista e nessun filtro attivo → stato vuoto.
      if (corta && !hasFilters) {
        svuota()
        return false
      }
      // Nessuna search e nessun filtro → stato vuoto (copre sia il primo
      // caricamento sia la search svuotata: la distinzione su `hasSearched`
      // serviva solo a risparmiare i reset, che ora vivono in `svuota`).
      if (!searchTerm && !hasFilters) {
        svuota()
        return false
      }
    }

    // Marca QUESTA chiamata prima di partire: al ritorno si scrive solo se nel
    // frattempo non ne e' partita una piu' recente.
    const tag = fv.tag()
    if (!silent) loading.value = true
    ricercaInviata = paramsRicerca(f, ricerca).search
    try {
      const res = await fetchPage(buildParams(f, searchTerm, ricerca))
      if (!fv.isCurrent(tag)) return false   // risposta stantia: la lista NON si tocca
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      // Campi extra dell'envelope, dopo il guard: vedi la nota su `onPayload`.
      if (onPayload) onPayload(res.data.data)
      hasSearched.value = true
      // `true` SOLO quando questa chiamata ha davvero scritto `items`: i
      // caller con lavoro derivato (es. listini → preload versioni) devono
      // poter distinguere «lista aggiornata» da «guardia/risposta scartata»,
      // altrimenti il secondo giro parte sui dati di un'altra chiamata.
      return true
    } catch (err) {
      // Una richiesta fallita non e' una lista a video: il tasto successivo
      // deve poter riprovare, anche con lo stesso termine.
      if (fv.isCurrent(tag)) ricercaInviata = NESSUNA_RICHIESTA
      throw err
    } finally {
      // Lo spinner lo spegne solo la fetch corrente: una risposta scartata che
      // lo spegnesse lascerebbe la lista senza indicazione mentre una chiamata
      // piu' recente e' ancora in volo.
      if (!silent && fv.isCurrent(tag)) loading.value = false
    }
  }

  // Scopo: il nuovo termine della casella cambia la richiesta? `false` se il
  //        parametro `search` che partirebbe e' lo stesso dell'ultima richiesta
  //        partita: allora non c'e' niente da rifare. Lo chiede `useSearchTable`
  //        prima di ricaricare a ogni tasto.
  // ⭐ Un termine sotto la soglia della lista NON e' una ricerca
  //    (`paramsRicerca` non lo manda): su una lista gia' a video, digitare il
  //    1° e il 2° carattere non cambia niente. Fino al 2026-09-26 li' ripartiva
  //    la STESSA richiesta senza `search` — sui preventivi (e sulle liste col
  //    filtro data di default, che conta come filtro attivo) una lista pesante
  //    ricaricata identica, che a video sembrava una ricerca partita al primo
  //    carattere. Stessa cosa per «abc » dopo «abc»: il `trim` la rende uguale.
  // ⚠️ `true` quando decide `fetchList` senza chiamare il backend: lista non
  //    ancora caricata (la guardia empty-state), lista sospesa, e le liste che
  //    partono piene con `ricercaCorta: 'svuota'`, che sul termine corto
  //    SVUOTANO per scelta (vedi sopra) — lo svuotamento e' locale.
  function ricercaCambiaLaRichiesta(termine) {
    if (sospesa.value || !hasSearched.value || ricercaInviata === NESSUNA_RICHIESTA) return true
    const ricerca = { minCaratteri: ricercaMinCaratteri.value }
    const f = { ...filters.value, search: termine }
    if (alwaysFetch && ricercaCorta === 'svuota' && termineCorto(termineRicerca(f), ricerca)) return true
    return paramsRicerca(f, ricerca).search !== ricercaInviata
  }

  return {
    items, totalRecords, loading, hasSearched, sospesa, ricercaFull, ricercaMinCaratteri,
    fetchList, svuota, ricercaCambiaLaRichiesta,
  }
}
