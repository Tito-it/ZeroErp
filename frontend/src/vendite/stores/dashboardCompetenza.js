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
} from '../api/dashboardCompetenza'

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
  const commesseOrderBy = ref('valore_tot')
  const commesseOrderDir = ref('desc')

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
      order_by: commesseOrderBy.value,
      order_dir: commesseOrderDir.value,
      ...paging,
    })
  )

  // Scopo: applica un evento @sort del DataTable commesse allo stato
  //        ordinamento (sortOrder 1 = asc, -1/altro = desc). Sort rimosso
  //        (sortField null) -> torna al default "valore totale" DESC. Solo
  //        stato: la ricarica (pagina 1) resta al caller.
  function applyCommesseSort(event) {
    commesseOrderBy.value = event.sortField || 'valore_tot'
    commesseOrderDir.value =
      event.sortField && event.sortOrder === 1 ? 'asc' : 'desc'
  }
  const erroriFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaErrori({
        competenza_mese: competenzaMese,
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
  }

  // Scopo: azzera il pannello errori (cambio mese/anno) e invalida le fetch.
  function resetErrori() {
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
    commesseOrderBy.value = 'valore_tot'
    commesseOrderDir.value = 'desc'
    commesseFetch.resetAll()
    erroriFetch.resetAll()
  }

  return {
    anno,
    meseIdx,
    stadioSelezionato,
    soloRitardo,
    commesseOrderBy,
    commesseOrderDir,
    mesi,
    commesse: commesseFetch.items,
    commesseCount: commesseFetch.count,
    commessePage: commesseFetch.page,
    commessePageSize: commesseFetch.pageSize,
    commesseLoading: commesseFetch.loading,
    applyCommessePage: commesseFetch.applyPageEvent,
    applyCommesseSort,
    errori: erroriFetch.items,
    erroriCount: erroriFetch.count,
    erroriPage: erroriFetch.page,
    erroriPageSize: erroriFetch.pageSize,
    erroriLoading: erroriFetch.loading,
    applyErroriPage: erroriFetch.applyPageEvent,
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
