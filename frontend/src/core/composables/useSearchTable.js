// Composable centralizzato per DataTable con ricerca, paginazione server-side e sort.
// Elimina la duplicazione di onPage/onSort/debounce search in ogni lista.
//
// Ricerca universale: legge automaticamente il termine di ricerca da:
//   1. route.query.search (navigazione diretta dal SearchDrawer)
//   2. contextStore.searchTerm (navigazione indiretta da menu/tab)
// Nessuna configurazione necessaria nelle singole SearchTable o View.
//
// Uso:
//   const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store)
//
// Nel template:
//   <DataTable v-bind="paginatorProps" lazy @page="onPage" @sort="onSort" ...>
//
// paginatorProps include: totalRecords, rows, first, rowsPerPageOptions,
//   paginator, paginatorTemplate, currentPageReportTemplate

import { ref, computed, watch, onMounted, onActivated, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useContextStore } from '../../stores/context'
import { MANAGE_ICONS } from '../constants'
import { QUERY_VIEWPORT_COMPATTO, USO_MISURA, misuraDefault, misuraPerViewport, misureOpzioni } from '../misurePagina'
import { SEARCH_DEBOUNCE_MS } from './useDebouncedAction'

export function useSearchTable(store, options = {}) {
  const {
    // Ritardo standard della ricerca a video: la costante vive in
    // `useDebouncedAction` insieme all'altra sede che la usa (i cruscotti, che
    // questo composable non puo' servire — pretende uno store «ricerca + sort +
    // limit»). Il timer qui resta suo, perche' ha una logica in piu'
    // (`skipNextDebounce` per i termini precaricati da ricerca universale/AI,
    // che devono partire SUBITO); a essere condiviso e' il valore, che e'
    // l'unica cosa che non deve divergere fra le due.
    debounceMs = SEARCH_DEBOUNCE_MS,
    extraFilters = null, // funzione che ritorna filtri aggiuntivi da applicare
    defaultSortField = null, // campo sort iniziale (es. 'descrizione')
    defaultSortOrder = 'asc', // direzione sort iniziale
    // ⭐ Lista INCORPORATA (pannello della home, sezione di una pagina che
    //    non e' la lista): non e' la lista di rotta, quindi non segue la
    //    ricerca universale (`?search=`, `ctx.searchTerm`). Senza, un pannello
    //    sotto KeepAlive si trova la casella riempita dall'ultima ricerca
    //    fatta altrove.
    //    F5 non e' piu' di qui (2026-10-04): e' il tasto dell'azione `reload`
    //    della barra (`useScorciatoie`), che sa quale lista e' a video.
    //    Il listener di qui restava su `window` sotto KeepAlive, e ogni F5
    //    ricaricava tutte le liste gia' visitate.
    incorporata = false,
  } = options

  const route = useRoute()
  const ctx = useContextStore()
  const { t } = useI18n()
  const initialLimit = store.filters.limit
  const useResponsiveDefaultRows = initialLimit === misuraDefault(USO_MISURA.PAGINA)
  const compactRowsQuery = typeof window !== 'undefined'
    ? window.matchMedia(QUERY_VIEWPORT_COMPATTO)
    : null
  let userChangedRows = false

  // Inizializza sort default nello store se non gia' impostato
  if (defaultSortField && !store.filters.order_by) {
    store.filters.order_by = defaultSortField
    store.filters.order_dir = defaultSortOrder
  }

  // Scopo: una ricerca ESTERNA (deep-link `?search=` da "apri documento",
  // ricerca universale, AI) deve trovare il documento OVUNQUE nel tempo:
  // azzera i default temporali UX (`data_da`/`data_a`) se la lista li usa.
  // Senza questo, i documenti piu' vecchi del default standard risultano
  // "non trovati" proprio quando qualcuno li cerca per codice (es. il
  // backlog fatturazione, ordinato per anzianita'). Il default e' una
  // scelta UX, non una regola dati: l'operatore lo vede azzerato nei
  // DatePicker (sync store→ref in useStoreFilterBindings) e puo' rimetterlo.
  // Le ricerche DIGITATE in pagina non toccano i filtri data scelti.
  function clearDateDefaultsForExternalSearch() {
    if ('data_da' in store.filters) store.filters.data_da = null
    if ('data_a' in store.filters) store.filters.data_a = null
  }

  // Risolve termine ricerca iniziale: route query > context > vuoto
  const resolvedSearch = incorporata ? '' : (route.query.search || ctx.searchTerm || '')
  const searchText = ref(resolvedSearch)
  // Ultimo `?search` di deep-link gia' consumato: serve a onActivated per
  // ri-applicare SOLO un deep-link NUOVO, non a re-imporre quello vecchio a
  // ogni riattivazione (altrimenti svuotare/modificare la ricerca in pagina
  // verrebbe annullato al rientro nel tab, finche' l'URL conserva ?search).
  let lastConsumedSearch = incorporata ? null : (route.query.search || null)
  if (resolvedSearch) {
    store.filters.search = resolvedSearch
    clearDateDefaultsForExternalSearch()
  }
  let searchTimeout = null
  let skipNextDebounce = false

  // Watch reattivo su ctx.searchTerm — gestisce nuove ricerche da SearchDrawer
  // e navigazione tra pagine con contesto attivo. Aggiorna immediatamente (no debounce).
  watch(() => ctx.searchTerm, (newTerm) => {
    if (incorporata) return
    const term = newTerm || ''
    if (term !== searchText.value) {
      clearTimeout(searchTimeout)
      skipNextDebounce = true
      searchText.value = term
      store.filters.search = term
      store.filters.offset = 0
      if (term) clearDateDefaultsForExternalSearch()
      store.fetchList()
    }
  })

  // Debounce search da input utente → aggiorna store.filters.search e resetta offset
  watch(searchText, () => {
    if (skipNextDebounce) {
      skipNextDebounce = false
      return
    }
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
      const termine = searchText.value || ''
      // ⭐ Se il termine non cambia la richiesta (sotto la soglia della lista,
      //    o uguale dopo il `trim`) la lista a video e' gia' la risposta: si
      //    allinea lo store e basta — ne' fetch ne' ritorno a pagina 1. Lo
      //    decide il BB di stato, che conosce soglia e ultima richiesta. Uno
      //    store che non lo espone ricarica a ogni tasto, come sempre.
      const cambia = store.ricercaCambiaLaRichiesta?.(termine) ?? true
      store.filters.search = termine
      if (!cambia) return
      store.filters.offset = 0
      store.fetchList()
    }, debounceMs)
  })

  // Scopo: ricarica lista mantenendo filtri e paginazione correnti
  function reload() {
    store.fetchList()
  }

  // Scopo: applica il default responsive solo alle liste standard che nascono
  // alla misura di pagina. Le liste che nascono compatte restano eccezioni esplicite.
  function applyResponsiveDefaultRows({ fetch = false } = {}) {
    if (!useResponsiveDefaultRows || userChangedRows) return
    const nextLimit = misuraPerViewport()
    if (store.filters.limit === nextLimit) return
    store.filters.limit = nextLimit
    store.filters.offset = 0
    if (fetch && store.hasSearched) store.fetchList()
  }

  function onRowsMediaChange() {
    applyResponsiveDefaultRows({ fetch: true })
  }

  applyResponsiveDefaultRows()

  onMounted(() => {
    compactRowsQuery?.addEventListener('change', onRowsMediaChange)
  })

  // Scopo: deep-link `?search=` verso una view gia' cachata da KeepAlive
  // (AppLayout usa `:key="$route.path"`: navigare allo stesso path con query
  // diversa RIATTIVA la view, non la rimonta, quindi il setup — unica lettura
  // di route.query.search, riga ~49 — non ri-esegue). Senza questo hook il
  // filtro da un deep-link (es. "apri documento" dalla dashboard fatturazione)
  // verrebbe ignorato dopo la prima visita della lista.
  // Idempotente: al primo mount searchText coincide gia' con la query (il
  // guard evita il doppio fetch); `skipNextDebounce` neutralizza il watch
  // debounced su searchText. Pattern memoria feedback_keepalive_onactivated.
  // Freshness (stessa memoria): la prima onActivated e' quella del mount — il
  // fetch iniziale e' gia' partito (o partira' dal flusso di ricerca), quindi
  // va saltata per non raddoppiarlo. Dalle riattivazioni successive in poi si
  // rinfresca la pagina corrente.
  let firstActivation = true
  // ⛔ E il refresh qui sotto DIPENDE da `store.hasSearched`: uno store che non
  //    lo espone lo disattiva in silenzio — `undefined && ...` e' falso, quindi
  //    la lista non ricarica mai al rientro e nessuno se ne accorge, perche' la
  //    pagina non sbaglia: e' solo ferma.
  // 🔴 Non e' un'ipotesi: il 2026-09-10 erano SETTE store di `amministrazione`
  //    (operatori, email account/log/template, famiglie documento, registri
  //    numerazione, mapping BA) — cioe' cinque liste di rotta il cui rientro
  //    sotto KeepAlive non ricaricava, mentre i loro commenti dichiaravano che
  //    lo scaffolding se ne stava occupando.
  // ⭐ Il difetto era muto perche' il BB LEGGE una proprieta' che il chiamante
  //    puo' dimenticare: qui non si puo' fare piu' che renderlo rumoroso, e si
  //    fa in DEV — `useListaEmptyStateFetch` e `useListaStoreCore` lo espongono
  //    entrambi, quindi mancarlo significa non averlo ri-esportato dallo store.
  if (import.meta.env.DEV && !('hasSearched' in store)) {
    console.warn(
      `[useSearchTable] lo store "${store.$id}" non espone \`hasSearched\`: il refresh ` +
      'al rientro sotto <KeepAlive> resta SPENTO, in silenzio. ' +
      'Ri-esportalo dal return dello store (lo producono sia `useListaEmptyStateFetch` ' +
      'sia `useListaStoreCore`).',
    )
  }
  onActivated(() => {
    const qs = incorporata ? null : route.query.search
    // Applica solo un deep-link NUOVO (query cambiata da quando l'abbiamo
    // consumata l'ultima volta), non a ogni riattivazione: preserva le
    // modifiche/lo svuotamento fatti dall'utente sulla ricerca in pagina.
    if (qs && qs !== lastConsumedSearch) {
      lastConsumedSearch = qs
      clearTimeout(searchTimeout)
      skipNextDebounce = true
      searchText.value = qs
      store.filters.search = qs
      store.filters.offset = 0
      clearDateDefaultsForExternalSearch()
      store.fetchList()
      firstActivation = false
      return
    }
    if (firstActivation) {
      firstActivation = false
      return
    }
    // Ri-attivazione senza deep-link nuovo: i dati possono essere stantii per
    // effetti collaterali maturati altrove (es. evasione da DDT -> ordine
    // EVASO, push commessa, resi). Refetch idempotente della PAGINA CORRENTE:
    // filtri/ricerca/offset invariati, cambia solo il contenuto righe. Guard
    // su hasSearched (liste a ricerca obbligatoria mai interrogate: nulla da
    // rinfrescare) e loading (niente accavallamento risposte).
    if (store.hasSearched && !store.loading) store.fetchList()
  })

  // Cleanup timeout e listener on unmount
  onUnmounted(() => {
    clearTimeout(searchTimeout)
    compactRowsQuery?.removeEventListener('change', onRowsMediaChange)
  })

  // Handler @page DataTable — guard contro loop infinito e click rapidi.
  // PrimeVue DataTable ri-emette @page quando items cambia; senza guard si crea un ciclo.
  // Se una richiesta è in volo, ignora il click per evitare accavallamento risposte.
  function onPage(event) {
    if (event.first === store.filters.offset && event.rows === store.filters.limit) return
    if (store.loading) return
    if (event.rows !== store.filters.limit) userChangedRows = true
    store.filters.offset = event.first
    store.filters.limit = event.rows
    store.fetchList()
  }

  // Handler @sort DataTable.
  // ⛔ LO STATO «ORDINAMENTO RIMOSSO» HA UNA SUA DIREZIONE: `null`, non `desc`.
  //    `removable-sort` alterna asc -> desc -> NIENTE, e nel terzo stato
  //    PrimeVue emette `sortField` e `sortOrder` nulli. Scriverli come
  //    `order_dir = 'desc'` — come faceva il ternario precedente, per cui
  //    «diverso da 1» voleva dire discendente — teneva la prop `sortOrder` a
  //    `-1` mentre il campo era sparito: al click seguente la prop NON cambiava
  //    valore, il watcher di PrimeVue non scattava, e la freccia restava a
  //    dire una cosa mentre i dati ne dicevano un'altra.
  // 🔴 Difetto reale, visto da Tid in collaudo sulla lista DDT il 2026-09-02:
  //    freccia ASC su dati DESC. Era latente da prima e non si notava perche'
  //    la direzione cambiava comunque a ogni click.
  function onSort(event) {
    store.filters.order_by = event.sortField || null
    store.filters.order_dir = event.sortField
      ? (event.sortOrder === -1 ? 'desc' : 'asc')
      : null
    store.fetchList()
  }

  // Applica filtri custom (chiamare quando cambiano filtri extra come comune_id)
  function applyFilters() {
    store.filters.search = searchText.value || ''
    store.filters.offset = 0
    if (extraFilters) {
      const extra = extraFilters()
      Object.assign(store.filters, extra)
    }
    store.fetchList()
  }

  // Scopo: lista priva di record. Heuristica generica: tutte le liste lazy
  // espongono totalRecords nel paginator -> 0 = niente da paginare = lista vuota.
  // Usata per disabilitare l'azione "reload" (nulla da ricaricare).
  const isListEmpty = computed(() => (store.totalRecords ?? 0) === 0)

  // Scopo: factory standard dell'azione "Ricarica lista" usata da PageActionsBar.
  // Centralizza icona+label+disable logic in modo che ogni consumer scriva una
  // sola riga (`reloadAction()`) invece di duplicare l'oggetto. `disabled` si
  // aggiorna reattivamente: se chiamata dentro un computed (pattern standard
  // pageActions), si rivaluta quando store.totalRecords cambia.
  function reloadAction(overrides = {}) {
    return {
      key: 'reload',
      kind: 'utility',
      label: t('common.reload_list'),
      icon: MANAGE_ICONS.RELOAD,
      disabled: isListEmpty.value,
      command: reload,
      ...overrides,
    }
  }

  // Props da passare al DataTable via v-bind (include paginazione e sort default)
  const paginatorProps = computed(() => ({
    totalRecords: store.totalRecords,
    rows: store.filters.limit,
    first: store.filters.offset,
    rowsPerPageOptions: misureOpzioni(),
    paginator: true,
    paginatorPosition: 'top',
    paginatorTemplate: 'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown JumpToPageDropdown CurrentPageReport',
    currentPageReportTemplate: '{currentPage}/{totalPages}',
    sortField: store.filters.order_by || null,
    sortOrder: store.filters.order_dir === 'desc' ? -1 : store.filters.order_dir === 'asc' ? 1 : null
  }))

  return {
    searchText,
    onPage,
    onSort,
    applyFilters,
    reload,
    isListEmpty,
    reloadAction,
    paginatorProps
  }
}
