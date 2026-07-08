// Store Pinia Situazione aperta v2 — serbatoio pre-commessa
// (brief-design-fatturazione-due-lenti §6-ter): riepilogo stock area × fase +
// lista documenti aperti-non-chiusi con filtri area/fase/ritardo_giorni.
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
  getDashboardAperto,
  listDashboardApertoDocumenti,
} from '../api/dashboardAperto'

export const useDashboardApertoStore = defineStore('vendite-dashboard-aperto', () => {
  // Filtri lista: area documento (null = tutte) e fase normalizzata
  // (null = tutte). ritardo_giorni (null = nessuna soglia): filtro "aperti da
  // oltre N giorni" su data documento (DL-17), solo sulla lista — le card del
  // riepilogo restano la fotografia completa.
  const areaSelezionata = ref(null)
  const faseSelezionata = ref(null)
  const ritardoGiorni = ref(null)

  // Riepilogo: array aree (4 sempre presenti, ordine funnel) + vocabolario
  // fasi top-level (alimenta il filtro della lista) dal BE. Fetch guardata
  // anti-race via BB useDashRiepilogo.
  const aree = ref([])
  const fasi = ref([])
  const riepilogo = useDashRiepilogo(getDashboardAperto, (data) => {
    aree.value = data.aree ?? []
    fasi.value = data.fasi ?? []
  })

  // Lista documenti: sezione paginata standard (axios omette da solo i
  // params null: nessuna coalescenza necessaria).
  const documentiFetch = usePagedDashFetch((paging) =>
    listDashboardApertoDocumenti({
      area: areaSelezionata.value,
      fase: faseSelezionata.value,
      ritardo_giorni: ritardoGiorni.value,
      ...paging,
    })
  )

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
    riepilogo.invalidate()
    areaSelezionata.value = null
    faseSelezionata.value = null
    ritardoGiorni.value = null
    aree.value = []
    fasi.value = []
    documentiFetch.resetAll()
  }

  return {
    areaSelezionata,
    faseSelezionata,
    ritardoGiorni,
    aree,
    fasi,
    documenti: documentiFetch.items,
    documentiCount: documentiFetch.count,
    documentiPage: documentiFetch.page,
    documentiPageSize: documentiFetch.pageSize,
    documentiLoading: documentiFetch.loading,
    documentiLoaded: documentiFetch.loaded,
    applyDocumentiPage: documentiFetch.applyPageEvent,
    fetchRiepilogo: riepilogo.fetchRiepilogo,
    fetchDocumenti,
    resetDocumenti,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (RLS/scope): reset al logout.
  userScoped: true,
})
