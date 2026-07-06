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
import { BREAKPOINTS, MANAGE_ICONS, PAGINATION } from '../constants'

export function useSearchTable(store, options = {}) {
  const {
    debounceMs = 400,
    extraFilters = null, // funzione che ritorna filtri aggiuntivi da applicare
    defaultSortField = null, // campo sort iniziale (es. 'descrizione')
    defaultSortOrder = 'asc' // direzione sort iniziale
  } = options

  const route = useRoute()
  const ctx = useContextStore()
  const { t } = useI18n()
  const initialLimit = store.filters.limit
  const useResponsiveDefaultRows = initialLimit === PAGINATION.DEFAULT_ROWS
  const compactRowsQuery = typeof window !== 'undefined'
    ? window.matchMedia(`(max-width: ${BREAKPOINTS.TABLET - 1}px)`)
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
  // Senza questo, i documenti piu' vecchi del default anno-1 risultano
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
  const resolvedSearch = route.query.search || ctx.searchTerm || ''
  const searchText = ref(resolvedSearch)
  // Ultimo `?search` di deep-link gia' consumato: serve a onActivated per
  // ri-applicare SOLO un deep-link NUOVO, non a re-imporre quello vecchio a
  // ogni riattivazione (altrimenti svuotare/modificare la ricerca in pagina
  // verrebbe annullato al rientro nel tab, finche' l'URL conserva ?search).
  let lastConsumedSearch = route.query.search || null
  if (resolvedSearch) {
    store.filters.search = resolvedSearch
    clearDateDefaultsForExternalSearch()
  }
  let searchTimeout = null
  let skipNextDebounce = false

  // Watch reattivo su ctx.searchTerm — gestisce nuove ricerche da SearchDrawer
  // e navigazione tra pagine con contesto attivo. Aggiorna immediatamente (no debounce).
  watch(() => ctx.searchTerm, (newTerm) => {
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
      store.filters.search = searchText.value || ''
      store.filters.offset = 0
      store.fetchList()
    }, debounceMs)
  })

  // Scopo: ricarica lista mantenendo filtri e paginazione correnti
  function reload() {
    store.fetchList()
  }

  function defaultRowsForViewport() {
    return compactRowsQuery?.matches ? PAGINATION.COMPACT_ROWS : PAGINATION.DEFAULT_ROWS
  }

  // Scopo: applica il default responsive solo alle liste standard che nascono
  // a 25 righe. Le rare liste che nascono a 10 restano eccezioni esplicite.
  function applyResponsiveDefaultRows({ fetch = false } = {}) {
    if (!useResponsiveDefaultRows || userChangedRows) return
    const nextLimit = defaultRowsForViewport()
    if (store.filters.limit === nextLimit) return
    store.filters.limit = nextLimit
    store.filters.offset = 0
    if (fetch && store.hasSearched) store.fetchList()
  }

  // Scopo: intercetta F5 per ricaricare la lista senza reload browser
  function onKeydown(e) {
    if (e.key === 'F5') {
      e.preventDefault()
      reload()
    }
  }
  function onRowsMediaChange() {
    applyResponsiveDefaultRows({ fetch: true })
  }

  applyResponsiveDefaultRows()

  onMounted(() => {
    window.addEventListener('keydown', onKeydown)
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
  onActivated(() => {
    const qs = route.query.search
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
    }
  })

  // Cleanup timeout e listener on unmount
  onUnmounted(() => {
    clearTimeout(searchTimeout)
    window.removeEventListener('keydown', onKeydown)
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

  // Handler @sort DataTable
  function onSort(event) {
    store.filters.order_by = event.sortField
    store.filters.order_dir = event.sortOrder === 1 ? 'asc' : 'desc'
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
    rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
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
