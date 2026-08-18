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
//  - `buildParams(f, searchTerm)` → object: la mappatura filtri→query params,
//    che differisce per dominio (es. preventivi usa page/page_size, offerte e
//    ordini usano limit/offset; nomi filtri diversi). Riceve `searchTerm` già
//    trimmato: il caller decide se/come passarlo (tipicamente se length >= 3).
//  - `fetchPage(params)` → Promise di una response axios con envelope standard
//    `{ data: { data: { results, count } } }` (paginated_envelope BE).
//  - `alwaysFetch` (default false): se true salta i guard empty-state e carica
//    SEMPRE (liste che partono piene: admin, geo). Il search < 3 char resta
//    ignorato da `buildParams`, quindi la lista resta piena mentre si digita
//    (no flash vuoto). Usato dalla factory `createCrudStore` con startsEmpty:false.
//
// Ritorna lo stato reattivo (items/totalRecords/loading/hasSearched/sospesa) +
// fetchList.
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
export function useListaEmptyStateFetch({ filters, hasActiveFilters = () => false, buildParams, fetchPage, alwaysFetch = false, ricercaCorta = 'fetch' }) {
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
  const fv = useFetchVersion()

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
    items.value = []
    totalRecords.value = 0
    hasSearched.value = false
    loading.value = false
  }

  async function fetchList() {
    if (sospesa.value) return false
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    // Liste che partono piene: comportamento della ricerca corta secondo
    // `ricercaCorta` (vedi sopra). Il default 'fetch' prosegue e basta.
    if (alwaysFetch && searchTerm.length > 0 && searchTerm.length < 3) {
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
      // Search con meno di 3 caratteri e nessun filtro attivo → stato vuoto.
      if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
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
    loading.value = true
    try {
      const res = await fetchPage(buildParams(f, searchTerm))
      if (!fv.isCurrent(tag)) return false   // risposta stantia: la lista NON si tocca
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
      // `true` SOLO quando questa chiamata ha davvero scritto `items`: i
      // caller con lavoro derivato (es. listini → preload versioni) devono
      // poter distinguere «lista aggiornata» da «guardia/risposta scartata»,
      // altrimenti il secondo giro parte sui dati di un'altra chiamata.
      return true
    } finally {
      // Lo spinner lo spegne solo la fetch corrente: una risposta scartata che
      // lo spegnesse lascerebbe la lista senza indicazione mentre una chiamata
      // piu' recente e' ancora in volo.
      if (fv.isCurrent(tag)) loading.value = false
    }
  }

  return { items, totalRecords, loading, hasSearched, sospesa, fetchList, svuota }
}
