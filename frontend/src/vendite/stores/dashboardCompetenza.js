// Store Pinia Lente 1 Competenza (brief-design-fatturazione-due-lenti §4):
// anno, mese selezionato, aggregata 12 mesi × 4 stadi, drill-down per commessa
// (DEC-4: una riga per commessa, dettaglio nel drawer) e pannello errori vivi.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (niente useApiHandler.execute su promise non-axios —
// memoria feedback_useapihandler_solo_axios).
// Le sezioni paginate (commesse, errori) usano il BB usePagedDashFetch
// (guard di versione + rientro pagina-oltre-l'ultima); l'aggregata ha il suo
// guard di versione dedicato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDashRiepilogo } from '../../core/composables/useDashRiepilogo'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { PAGINATION } from '../../core/constants'
import {
  getDashboardCompetenza,
  listDashboardCompetenzaCommesse,
  listDashboardCompetenzaErrori,
  listDashboardCompetenzaGruppi,
} from '../api/dashboardCompetenza'

// Stadio del funnel il cui drill-down NON è la lista commesse ma la lista dei
// GRUPPI FATTURABILI: è l'unico stadio in cui il verbo è «Fattura», e si
// fattura un documento (o gli oneri di una commessa), non una commessa —
// che è multi-sorgente e quindi non isola nulla. Costante unica: la usano il
// gate della fetch e il template.
export const STADIO_GRUPPI = 'DA_EMETTERE'

// Riepilogo di perimetro vuoto: forma stabile per il render prima della prima
// risposta (mai `undefined` nel template).
const RIEPILOGO_VUOTO = { n_gruppi: 0, n_attivita: 0, valore: null, n_gruppi_oneri: 0 }

// Scopo: stato di ordinamento server-side di una lista lazy del cruscotto —
//        i due ref (colonna + direzione) e l'handler che applica l'evento
//        @sort del DataTable. Estratto alla 2ª occorrenza (commesse + gruppi,
//        regola del 2, ok Tid 2026-07-27): erano due copie identiche salvo la
//        colonna di default.
//        Convenzione PrimeVue: `sortOrder === 1` = asc; sort RIMOSSO
//        (`sortField` null) = ritorno al default della lista, non "nessun
//        ordinamento" — su una lista paginata server-side un ordine assente
//        renderebbe la paginazione non deterministica.
//        Solo stato: la ricarica (che riparte da pagina 1) resta al caller,
//        che ha la sua gestione errori.
function useSortState(defaultBy, defaultDir = 'desc') {
  const orderBy = ref(defaultBy)
  const orderDir = ref(defaultDir)
  function apply(event) {
    orderBy.value = event.sortField || defaultBy
    orderDir.value = event.sortField && event.sortOrder === 1 ? 'asc' : defaultDir
  }
  function reset() {
    orderBy.value = defaultBy
    orderDir.value = defaultDir
  }
  return { orderBy, orderDir, apply, reset }
}

export const useDashboardCompetenzaStore = defineStore('vendite-dashboard-competenza', () => {
  const anno = ref(new Date().getFullYear())
  // Indice 0-11 del mese selezionato (default: mese corrente).
  const meseIdx = ref(new Date().getMonth())
  // Stadio selezionato per il drill-down (null = nessuna card attiva).
  const stadioSelezionato = ref(null)
  // Filtro recuperi tardivi del drill-down (solo attivita' emesse in ritardo).
  const soloRitardo = ref(false)

  // Ordinamento del drill-down per commessa (convenzione order_by/order_dir come
  // le liste standard): default "valore totale" DESC (le commesse piu' pesanti
  // prima). Lista lazy (paginata server-side) -> ordinamento server-side,
  // corretto su TUTTE le pagine. Si ordina per gli AGGREGATI, non per la riga.
  const commesseSort = useSortState('valore_tot')

  // Aggregata: array 12 mesi { competenza_mese, stadi, totali, n_errori }
  // dal BE. Fetch guardata anti-race via BB useDashRiepilogo: scarta la
  // risposta se nel frattempo l'anno e' cambiato di nuovo (vince l'ultima
  // richiesta, non l'ultima risposta arrivata).
  const mesi = ref([])
  const aggregata = useDashRiepilogo(
    () => getDashboardCompetenza(anno.value),
    (data) => {
      mesi.value = data.mesi ?? []
    }
  )

  // Drill-down per commessa + pannello errori: sezioni paginate standard.
  const commesseFetch = usePagedDashFetch((paging, competenzaMese) =>
    listDashboardCompetenzaCommesse({
      competenza_mese: competenzaMese,
      stadio: stadioSelezionato.value,
      solo_ritardo: soloRitardo.value,
      order_by: commesseSort.orderBy.value,
      order_dir: commesseSort.orderDir.value,
      ...paging,
    })
  )

  // Drill-down GRUPPI FATTURABILI (card «Da emettere»): stessa meccanica delle
  // altre sezioni paginate, piu' il `riepilogo` di perimetro che il BE mette
  // nell'envelope. Il riepilogo NON si somma dalle righe della pagina: sarebbe
  // un parziale che sembra un totale, e nessuno somma a mano piu' pagine per
  // accorgersene.
  const gruppiSort = useSortState('valore')
  const gruppiRiepilogo = ref({ ...RIEPILOGO_VUOTO })
  // Filtro «tipo documento/sorgente». `null` = tutti (parametro omesso), stessa
  // convenzione dello stadio: il default non e' un valore speciale da gestire,
  // e' l'assenza del filtro.
  const gruppiTipo = ref(null)
  // Voci del filtro, calcolate dal BE SUI DATI del perimetro: solo cio' che
  // esiste davvero, con il conteggio. Non seguono il filtro (se lo seguissero,
  // scegliendo un tipo le altre voci sparirebbero dalla tendina).
  const gruppiTipi = ref([])
  const gruppiFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaGruppi({
        competenza_mese: competenzaMese,
        stadio: STADIO_GRUPPI,
        tipo_gruppo: gruppiTipo.value,
        order_by: gruppiSort.orderBy.value,
        order_dir: gruppiSort.orderDir.value,
        ...paging,
      }),
    {
      onPayload: (payload) => {
        gruppiRiepilogo.value = payload.riepilogo ?? { ...RIEPILOGO_VUOTO }
        gruppiTipi.value = payload.tipi ?? []
      },
    }
  )

  // Scopo: carica una pagina di gruppi fatturabili del mese. Parte solo sullo
  //        stadio che ha «Fattura» come verbo: sugli altri la lista di
  //        riferimento resta quella per commessa.
  async function fetchGruppi(competenzaMese) {
    if (stadioSelezionato.value !== STADIO_GRUPPI) return
    await gruppiFetch.fetch(competenzaMese)
  }

  // Scopo: azzera la lista gruppi (cambio mese/stadio) incluso il riepilogo —
  //        lasciarlo indietro mostrerebbe i totali del contesto precedente
  //        sopra una lista vuota.
  function resetGruppi() {
    gruppiFetch.reset()
    gruppiRiepilogo.value = { ...RIEPILOGO_VUOTO }
    gruppiTipo.value = null
    gruppiTipi.value = []
  }

  // Ordinamento del pannello errori: default `data_evento desc` (eventi
  // recenti prima), che replica il default del BE e il preset del seed — la
  // lista non si riordina sotto gli occhi al primo caricamento.
  const erroriSort = useSortState('data_evento')
  const erroriFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaErrori({
        competenza_mese: competenzaMese,
        order_by: erroriSort.orderBy.value,
        order_dir: erroriSort.orderDir.value,
        ...paging,
      }),
    { defaultPageSize: PAGINATION.COMPACT_ROWS }
  )

  // Scopo: carica una pagina di commesse per (mese, stadio selezionato,
  //        filtro ritardo). Senza stadio attivo non parte nessuna fetch.
  async function fetchCommesse(competenzaMese) {
    if (!stadioSelezionato.value) return
    await commesseFetch.fetch(competenzaMese)
  }

  // Scopo: carica una pagina di errori vivi del mese (blocco 4).
  async function fetchErrori(competenzaMese) {
    await erroriFetch.fetch(competenzaMese)
  }

  // Scopo: azzera il drill-down (cambio mese/anno o deselezione card) e
  //        invalida le fetch in volo.
  function resetCommesse() {
    stadioSelezionato.value = null
    soloRitardo.value = false
    commesseFetch.reset()
    // Il drill-down e' UNO solo: deselezionare la card deve azzerare anche la
    // lista gruppi, altrimenti resterebbe a video appesa a uno stadio che non
    // e' piu' selezionato.
    resetGruppi()
  }

  // Scopo: azzera il pannello errori (cambio mese/anno) e invalida le fetch.
  function resetErrori() {
    erroriSort.reset()
    erroriFetch.reset()
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped) —
  //        resetAll riporta anche le pageSize al default (stato utente).
  function clearUserState() {
    aggregata.invalidate()
    anno.value = new Date().getFullYear()
    meseIdx.value = new Date().getMonth()
    mesi.value = []
    stadioSelezionato.value = null
    soloRitardo.value = false
    commesseSort.reset()
    commesseFetch.resetAll()
    gruppiSort.reset()
    gruppiRiepilogo.value = { ...RIEPILOGO_VUOTO }
    gruppiTipo.value = null
    gruppiTipi.value = []
    gruppiFetch.resetAll()
    erroriSort.reset()
    erroriFetch.resetAll()
  }

  return {
    anno,
    meseIdx,
    stadioSelezionato,
    soloRitardo,
    commesseOrderBy: commesseSort.orderBy,
    commesseOrderDir: commesseSort.orderDir,
    mesi,
    commesse: commesseFetch.items,
    commesseCount: commesseFetch.count,
    commessePage: commesseFetch.page,
    commessePageSize: commesseFetch.pageSize,
    commesseLoading: commesseFetch.loading,
    applyCommessePage: commesseFetch.applyPageEvent,
    applyCommesseSort: commesseSort.apply,
    gruppi: gruppiFetch.items,
    gruppiCount: gruppiFetch.count,
    gruppiPage: gruppiFetch.page,
    gruppiPageSize: gruppiFetch.pageSize,
    gruppiLoading: gruppiFetch.loading,
    gruppiLoaded: gruppiFetch.loaded,
    gruppiOrderBy: gruppiSort.orderBy,
    gruppiOrderDir: gruppiSort.orderDir,
    gruppiRiepilogo,
    gruppiTipo,
    gruppiTipi,
    applyGruppiPage: gruppiFetch.applyPageEvent,
    applyGruppiSort: gruppiSort.apply,
    fetchGruppi,
    resetGruppi,
    errori: erroriFetch.items,
    erroriCount: erroriFetch.count,
    erroriPage: erroriFetch.page,
    erroriPageSize: erroriFetch.pageSize,
    erroriLoading: erroriFetch.loading,
    applyErroriPage: erroriFetch.applyPageEvent,
    erroriOrderBy: erroriSort.orderBy,
    erroriOrderDir: erroriSort.orderDir,
    applyErroriSort: erroriSort.apply,
    fetchMensile: aggregata.fetchRiepilogo,
    fetchCommesse,
    fetchErrori,
    resetCommesse,
    resetErrori,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (scope GUC fail-closed): reset al logout.
  userScoped: true,
})
