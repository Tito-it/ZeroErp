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
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import {
  getDashboardBacklog,
  listDashboardBacklogDocumenti,
} from '../api/dashboardBacklog'

export const useDashboardBacklogStore = defineStore('vendite-dashboard-backlog', () => {
  // Filtri lista: classe di azionabilita' (null = tutte) e area (null = tutte).
  const classeSelezionata = ref(null)
  const areaSelezionata = ref(null)

  // Contatori di testata: array classi (3 sempre presenti) dal BE.
  const classi = ref([])
  const fvRiepilogo = useFetchVersion()

  // Lista documenti: sezione paginata standard (axios omette da solo i
  // params null: nessuna coalescenza necessaria).
  const documentiFetch = usePagedDashFetch((paging) =>
    listDashboardBacklogDocumenti({
      classe: classeSelezionata.value,
      area: areaSelezionata.value,
      ...paging,
    })
  )

  // Scopo: carica i contatori per classe. Il guard di versione scarta la
  // risposta se nel frattempo e' partito un refresh piu' nuovo.
  async function fetchRiepilogo() {
    const t = fvRiepilogo.tag()
    const res = await getDashboardBacklog()
    if (!fvRiepilogo.isCurrent(t)) return
    classi.value = res.data?.data?.classi ?? []
  }

  // Scopo: carica una pagina della lista coi filtri correnti.
  async function fetchDocumenti() {
    await documentiFetch.fetch()
  }

  // Scopo: azzera la lista (cambio filtri) e invalida le fetch in volo.
  function resetDocumenti() {
    documentiFetch.reset()
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped) —
  //        resetAll riporta anche la pageSize al default (stato utente).
  function clearUserState() {
    fvRiepilogo.invalidate()
    classeSelezionata.value = null
    areaSelezionata.value = null
    classi.value = []
    documentiFetch.resetAll()
  }

  return {
    classeSelezionata,
    areaSelezionata,
    classi,
    documenti: documentiFetch.items,
    documentiCount: documentiFetch.count,
    documentiPage: documentiFetch.page,
    documentiPageSize: documentiFetch.pageSize,
    documentiLoading: documentiFetch.loading,
    documentiLoaded: documentiFetch.loaded,
    applyDocumentiPage: documentiFetch.applyPageEvent,
    fetchRiepilogo,
    fetchDocumenti,
    resetDocumenti,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (RLS/scope): reset al logout.
  userScoped: true,
})
