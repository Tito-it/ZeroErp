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
import { USO_MISURA, misuraDefault } from '../misurePagina'

// Scopo: crea lo stato e le action di una sezione paginata.
// - fetchPage: (paging: {limit, offset}, ...args) => Promise (axios) verso
//   un endpoint con envelope paginato standard {data: {results, count, ...}}.
//   Gli ...args extra di fetch() vengono inoltrati (es. competenza_mese).
// - misura: l'USO della sezione (`USO_MISURA.PAGINA` di default,
//   `USO_MISURA.COMPATTA` per un drill-down): il numero di righe di partenza
//   lo dice il catalogo DB (BB `core/misurePagina`).
// - onPayload(payload): hook opzionale (2026-07-27) per i campi EXTRA che
//   l'endpoint mette accanto a results/count — es. il `riepilogo` di perimetro
//   della lista gruppi fatturabili. Viene invocato SOLO dopo il guard di
//   versione: agganciare quei campi fuori di qui (tappando la promise nel
//   fetchPage del caller) li applicherebbe anche alle risposte scartate, e la
//   riga di totali finirebbe a raccontare un contesto diverso dalla lista che
//   le sta sopra. Omesso = comportamento invariato per gli altri consumer.
// `loaded` = almeno una fetch riuscita (non scartata) dopo l'ultimo reset:
// distingue "lista davvero vuota" da "mai caricata / fetch fallita" — il
// caller NON deve mostrare un empty-state positivo se loaded e' false.
// Ritorna { items, count, page, pageSize, loading, loaded, fetch, reset, resetAll }.
export function usePagedDashFetch(
  fetchPage,
  { misura = USO_MISURA.PAGINA, onPayload = null } = {},
) {
  const defaultPageSize = misuraDefault(misura)
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
        // ⭐ La finestra, non la pagina (2026-10-21, un dialetto solo): la
        //    pagina e' lo stato del paginatore, il backend legge limit/offset.
        { limit: pageSize.value, offset: (page.value - 1) * pageSize.value },
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
      // Campi extra dell'envelope (es. riepilogo di perimetro): applicati solo
      // qui dentro, cioe' solo per una risposta che ha superato il guard.
      if (onPayload) onPayload(payload)
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
