// Store Pinia Lente 1 Competenza (brief-design-fatturazione-due-lenti §4):
// anno, mese selezionato, aggregata 12 mesi × 4 stadi, drill-down attivita'
// per stadio e pannello errori vivi del mese.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (niente useApiHandler.execute su promise non-axios —
// memoria feedback_useapihandler_solo_axios).
// Le sezioni paginate (attivita', errori) usano il BB usePagedDashFetch
// (guard di versione + rientro pagina-oltre-l'ultima); l'aggregata ha il suo
// guard di versione dedicato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDashRiepilogo } from '../../core/composables/useDashRiepilogo'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { PAGINATION } from '../../core/constants'
import {
  getDashboardCompetenza,
  listDashboardCompetenzaAttivita,
  listDashboardCompetenzaErrori,
} from '../api/dashboardCompetenza'

export const useDashboardCompetenzaStore = defineStore('vendite-dashboard-competenza', () => {
  const anno = ref(new Date().getFullYear())
  // Indice 0-11 del mese selezionato (default: mese corrente).
  const meseIdx = ref(new Date().getMonth())
  // Stadio selezionato per il drill-down attivita' (null = nessuna card attiva).
  const stadioSelezionato = ref(null)
  // Filtro recuperi tardivi del drill-down (solo attivita' emesse in ritardo).
  const soloRitardo = ref(false)

  // Ordinamento del drill-down attivita' (convenzione order_by/order_dir come
  // le liste standard): default "data attivita'" DESC. Lista lazy (paginata
  // server-side) -> ordinamento server-side, corretto su TUTTE le pagine.
  // Ordina per la COLONNA data, non per la stringa gg/mm/aaaa mostrata.
  const attivitaOrderBy = ref('data_attivita')
  const attivitaOrderDir = ref('desc')

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

  // Drill-down attivita' + pannello errori: sezioni paginate standard.
  const attivitaFetch = usePagedDashFetch((paging, competenzaMese) =>
    listDashboardCompetenzaAttivita({
      competenza_mese: competenzaMese,
      stadio: stadioSelezionato.value,
      solo_ritardo: soloRitardo.value,
      order_by: attivitaOrderBy.value,
      order_dir: attivitaOrderDir.value,
      ...paging,
    })
  )

  // Scopo: applica un evento @sort del DataTable attivita' allo stato
  //        ordinamento (sortOrder 1 = asc, -1/altro = desc). Sort rimosso
  //        (sortField null) -> torna al default "data attivita'" DESC. Solo
  //        stato: la ricarica (pagina 1) resta al caller.
  function applyAttivitaSort(event) {
    attivitaOrderBy.value = event.sortField || 'data_attivita'
    attivitaOrderDir.value =
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

  // Scopo: carica una pagina di attivita' per (mese, stadio selezionato,
  //        filtro ritardo). Senza stadio attivo non parte nessuna fetch.
  async function fetchAttivita(competenzaMese) {
    if (!stadioSelezionato.value) return
    await attivitaFetch.fetch(competenzaMese)
  }

  // Scopo: carica una pagina di errori vivi del mese (blocco 4).
  async function fetchErrori(competenzaMese) {
    await erroriFetch.fetch(competenzaMese)
  }

  // Scopo: azzera il drill-down attivita' (cambio mese/anno o deselezione
  //        card) e invalida le fetch in volo.
  function resetAttivita() {
    stadioSelezionato.value = null
    soloRitardo.value = false
    attivitaFetch.reset()
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
    attivitaOrderBy.value = 'data_attivita'
    attivitaOrderDir.value = 'desc'
    attivitaFetch.resetAll()
    erroriFetch.resetAll()
  }

  return {
    anno,
    meseIdx,
    stadioSelezionato,
    soloRitardo,
    attivitaOrderBy,
    attivitaOrderDir,
    mesi,
    attivita: attivitaFetch.items,
    attivitaCount: attivitaFetch.count,
    attivitaPage: attivitaFetch.page,
    attivitaPageSize: attivitaFetch.pageSize,
    attivitaLoading: attivitaFetch.loading,
    applyAttivitaPage: attivitaFetch.applyPageEvent,
    applyAttivitaSort,
    errori: erroriFetch.items,
    erroriCount: erroriFetch.count,
    erroriPage: erroriFetch.page,
    erroriPageSize: erroriFetch.pageSize,
    erroriLoading: erroriFetch.loading,
    applyErroriPage: erroriFetch.applyPageEvent,
    fetchMensile: aggregata.fetchRiepilogo,
    fetchAttivita,
    fetchErrori,
    resetAttivita,
    resetErrori,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (scope GUC fail-closed): reset al logout.
  userScoped: true,
})
