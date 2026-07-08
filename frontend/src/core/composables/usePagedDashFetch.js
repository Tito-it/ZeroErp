// Scopo: Sezione paginata dei cruscotti (drill-down attivita'/errori/
//        documenti): fetch con guard di versione anti-race, unwrap
//        dell'envelope paginato standard, adozione della PAGINA EFFETTIVA
//        dichiarata dal BE (dal 2026-07-07 gli endpoint dash clampano
//        l'offset all'ultima pagina in UNA sola valutazione della union:
//        il rientro da pagina stantia non costa piu' un secondo giro),
//        fallback di rientro in pagina 1 per endpoint senza clamp, e flag
//        loading corretto anche su risposte scartate. Estratto 2026-07-06
//        (regola del 2, ok Tid). Consumer: store dashboardCompetenza
//        (attivita'/errori), dashboardBacklog e dashboardAperto (documenti).
//        Costruito sopra useFetchVersion.
import { ref } from 'vue'
import { useFetchVersion } from './useFetchVersion'
import { PAGINATION } from '../constants'

// Scopo: crea lo stato e le action di una sezione paginata.
// - fetchPage: (paging: {page, page_size}, ...args) => Promise (axios) verso
//   un endpoint con envelope paginato standard {data: {results, count, ...}}.
//   Gli ...args extra di fetch() vengono inoltrati (es. competenza_mese).
// - defaultPageSize: default PAGINATION.DEFAULT_ROWS.
// `loaded` = almeno una fetch riuscita (non scartata) dopo l'ultimo reset:
// distingue "lista davvero vuota" da "mai caricata / fetch fallita" — il
// caller NON deve mostrare un empty-state positivo se loaded e' false.
// Ritorna { items, count, page, pageSize, loading, loaded, fetch, reset, resetAll }.
export function usePagedDashFetch(fetchPage, { defaultPageSize = PAGINATION.DEFAULT_ROWS } = {}) {
  const items = ref([])
  const count = ref(0)
  const page = ref(1)
  const pageSize = ref(defaultPageSize)
  const loading = ref(false)
  const loaded = ref(false)
  const fv = useFetchVersion()

  // Scopo: carica la pagina corrente. Il guard di versione scarta le risposte
  //        stantie (cambio contesto/pagina veloce: vince l'ultima richiesta,
  //        non l'ultima risposta arrivata).
  async function fetch(...args) {
    const t = fv.tag()
    loading.value = true
    try {
      const res = await fetchPage(
        { page: page.value, page_size: pageSize.value },
        ...args
      )
      if (!fv.isCurrent(t)) return
      const payload = res.data?.data ?? {}
      items.value = payload.results ?? []
      count.value = payload.count ?? 0
      // Adotta la pagina EFFETTIVA dichiarata dal BE: sugli endpoint dash il
      // clamp SQL serve direttamente l'ultima pagina reale quando quella
      // richiesta e' oltre la fine (envelope page != richiesta).
      page.value = payload.page ?? page.value
      loaded.value = true
      // Fallback per endpoint senza clamp BE: pagina oltre l'ultima, torna
      // alla prima e ricarica.
      if (items.value.length === 0 && count.value > 0 && page.value > 1) {
        page.value = 1
        await fetch(...args)
      }
    } finally {
      if (fv.isCurrent(t)) loading.value = false
    }
  }

  // Scopo: azzera la sezione (cambio contesto) e invalida le fetch in volo.
  //        La pageSize scelta dall'utente sopravvive di proposito (cambio
  //        mese/filtro non e' un cambio utente).
  function reset() {
    fv.invalidate()
    items.value = []
    count.value = 0
    page.value = 1
    loading.value = false
    loaded.value = false
  }

  // Scopo: reset completo per logout (userScoped): come reset() ma riporta
  //        anche la pageSize al default — lo stato utente non deve
  //        sopravvivere al cambio operatore.
  function resetAll() {
    reset()
    pageSize.value = defaultPageSize
  }

  // Scopo: applica un evento @page del DataTable lazy (paginator top) allo
  //        stato pagina/dimensione — solo stato, la fetch resta al caller
  //        (che ha la sua gestione errori). Unifica il calcolo pagina
  //        1-based dai campi first/rows di PrimeVue.
  function applyPageEvent(event) {
    pageSize.value = event.rows
    page.value = Math.floor(event.first / event.rows) + 1
  }

  return {
    items,
    count,
    page,
    pageSize,
    loading,
    loaded,
    fetch,
    reset,
    resetAll,
    applyPageEvent,
  }
}
