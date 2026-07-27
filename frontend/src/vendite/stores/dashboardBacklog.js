// Store Pinia Lente 2 Backlog (brief-design-fatturazione-due-lenti §5):
// contatori per classe di azionabilita' + lista documenti per anzianita'
// con filtri classe/area.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (memoria feedback_useapihandler_solo_axios).
// La lista usa il BB usePagedDashFetch (guard di versione + rientro
// pagina-oltre-l'ultima); il riepilogo ha il suo guard dedicato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDashRiepilogo } from '../../core/composables/useDashRiepilogo'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import {
  getDashboardBacklog,
  listDashboardBacklogDocumenti,
} from '../api/dashboardBacklog'

export const useDashboardBacklogStore = defineStore('vendite-dashboard-backlog', () => {
  // Filtri lista: classe di azionabilita' (null = tutte), area (null = tutte) e
  // ritardo_giorni "fermo da oltre N giorni" (null = nessuna soglia). Il
  // ritardo filtra SOLO la lista: le card per classe restano la fotografia
  // completa (stessa scelta della Situazione aperta).
  const classeSelezionata = ref(null)
  const areaSelezionata = ref(null)
  const ritardoGiorni = ref(null)

  // Ordinamento lista (convenzione order_by/order_dir come le liste standard):
  // default "fermo da" DESC = i piu' anziani prima. Lista lazy (paginata
  // server-side) -> ordinamento server-side, corretto su TUTTE le pagine.
  const orderBy = ref('anzianita_giorni')
  const orderDir = ref('desc')

  // Contatori di testata: array classi (3 sempre presenti) dal BE. Fetch
  // guardata anti-race via BB useDashRiepilogo.
  const classi = ref([])
  const riepilogo = useDashRiepilogo(getDashboardBacklog, (data) => {
    classi.value = data.classi ?? []
  })

  // Lista documenti: sezione paginata standard (axios omette da solo i
  // params null: nessuna coalescenza necessaria).
  const documentiFetch = usePagedDashFetch((paging) =>
    listDashboardBacklogDocumenti({
      classe: classeSelezionata.value,
      area: areaSelezionata.value,
      ritardo_giorni: ritardoGiorni.value,
      order_by: orderBy.value,
      order_dir: orderDir.value,
      ...paging,
    })
  )

  // Scopo: carica una pagina della lista coi filtri correnti.
  async function fetchDocumenti() {
    await documentiFetch.fetch()
  }

  // Scopo: applica un evento @sort del DataTable allo stato ordinamento
  //        (sortOrder 1 = asc, -1/altro = desc). Sort rimosso (sortField null)
  //        -> torna al default "fermo da" DESC. Solo stato: la ricarica
  //        (pagina 1) resta al caller, come per i cambi filtro.
  function applyDocumentiSort(event) {
    orderBy.value = event.sortField || 'anzianita_giorni'
    orderDir.value = event.sortField && event.sortOrder === 1 ? 'asc' : 'desc'
  }

  // Scopo: azzera la lista (cambio filtri) e invalida le fetch in volo.
  function resetDocumenti() {
    documentiFetch.reset()
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped) —
  //        resetAll riporta anche la pageSize al default (stato utente).
  function clearUserState() {
    riepilogo.invalidate()
    classeSelezionata.value = null
    areaSelezionata.value = null
    ritardoGiorni.value = null
    orderBy.value = 'anzianita_giorni'
    orderDir.value = 'desc'
    classi.value = []
    documentiFetch.resetAll()
  }

  return {
    classeSelezionata,
    areaSelezionata,
    ritardoGiorni,
    orderBy,
    orderDir,
    classi,
    documenti: documentiFetch.items,
    documentiCount: documentiFetch.count,
    documentiPage: documentiFetch.page,
    documentiPageSize: documentiFetch.pageSize,
    documentiLoading: documentiFetch.loading,
    documentiLoaded: documentiFetch.loaded,
    applyDocumentiPage: documentiFetch.applyPageEvent,
    applyDocumentiSort,
    fetchRiepilogo: riepilogo.fetchRiepilogo,
    fetchDocumenti,
    resetDocumenti,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (RLS/scope): reset al logout.
  userScoped: true,
})
