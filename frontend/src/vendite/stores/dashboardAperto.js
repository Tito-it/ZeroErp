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

  // Ordinamento lista (convenzione order_by/order_dir come le liste standard,
  // es. clienti/soggetti): default "aperto da" DESC = i piu' in essere da
  // prima. La lista e' lazy (paginata server-side) -> l'ordinamento DEVE essere
  // server-side per essere corretto su TUTTE le pagine, non solo su quella
  // visibile.
  const orderBy = ref('anzianita_giorni')
  const orderDir = ref('desc')

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
      order_by: orderBy.value,
      order_dir: orderDir.value,
      ...paging,
    })
  )

  // Scopo: applica un evento @sort del DataTable allo stato ordinamento
  //        (convenzione standard: sortOrder 1 = asc, -1/altro = desc). Sort
  //        rimosso (sortField null) -> torna al default "aperto da" DESC, cosi'
  //        la lista ha sempre un ordine definito. Solo stato: la ricarica
  //        (pagina 1) resta al caller, come per i cambi filtro.
  function applyDocumentiSort(event) {
    orderBy.value = event.sortField || 'anzianita_giorni'
    orderDir.value = event.sortField && event.sortOrder === 1 ? 'asc' : 'desc'
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
    riepilogo.invalidate()
    areaSelezionata.value = null
    faseSelezionata.value = null
    ritardoGiorni.value = null
    orderBy.value = 'anzianita_giorni'
    orderDir.value = 'desc'
    aree.value = []
    fasi.value = []
    documentiFetch.resetAll()
  }

  return {
    areaSelezionata,
    faseSelezionata,
    ritardoGiorni,
    orderBy,
    orderDir,
    aree,
    fasi,
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
