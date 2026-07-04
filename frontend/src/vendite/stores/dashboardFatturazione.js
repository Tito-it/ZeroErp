// Store Pinia Dashboard Fatturazione (brief-design-dashboard-fatturazione §7):
// anno, mese selezionato, matrice mensile e drill-down fermi.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (niente useApiHandler.execute su promise non-axios —
// memoria feedback_useapihandler_solo_axios).
// Guard di versione (useFetchVersion) su entrambe le fetch: cambi rapidi di
// anno/area/pagina non lasciano che una risposta stantia sovrascriva lo stato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { PAGINATION } from '../../core/constants'
import {
  getDashboardFatturazione,
  listDashboardFatturazioneFermi,
} from '../api/dashboardFatturazione'

export const useDashboardFatturazioneStore = defineStore('vendite-dashboard-fatturazione', () => {
  const anno = ref(new Date().getFullYear())
  // Indice 0-11 del mese selezionato (default: mese corrente).
  const meseIdx = ref(new Date().getMonth())
  // Area selezionata per il drill-down fermi (null = nessuna card attiva).
  const areaSelezionata = ref(null)

  // Matrice: array 12 mesi { competenza_mese, aree: [...] } dal BE (D-5).
  const mesi = ref([])

  // Drill-down fermi (envelope paginato standard).
  const fermi = ref([])
  const fermiCount = ref(0)
  const fermiPage = ref(1)
  const fermiPageSize = ref(PAGINATION.DEFAULT_ROWS)
  const fermiLoading = ref(false)

  const fvMatrice = useFetchVersion()
  const fvFermi = useFetchVersion()

  // Scopo: carica la matrice dell'anno corrente dello store. Il guard di
  // versione scarta la risposta se nel frattempo l'anno e' cambiato di nuovo
  // (doppio click sulle frecce: vince l'ultima richiesta, non l'ultima
  // risposta arrivata).
  async function fetchMatrice() {
    const t = fvMatrice.tag()
    const res = await getDashboardFatturazione(anno.value)
    if (!fvMatrice.isCurrent(t)) return
    mesi.value = res.data?.data?.mesi ?? []
  }

  // Scopo: carica una pagina di fermi per (mese selezionato, area selezionata).
  //        Guard di versione contro risposte stantie (cambio area/pagina
  //        veloce); se la pagina corrente e' oltre l'ultima (lista ridotta da
  //        altri utenti tra un refresh e l'altro) rientra sulla pagina 1.
  async function fetchFermi(competenzaMese) {
    if (!areaSelezionata.value) return
    const t = fvFermi.tag()
    fermiLoading.value = true
    try {
      const res = await listDashboardFatturazioneFermi({
        competenza_mese: competenzaMese,
        area: areaSelezionata.value,
        page: fermiPage.value,
        page_size: fermiPageSize.value,
      })
      if (!fvFermi.isCurrent(t)) return
      const payload = res.data?.data ?? {}
      fermi.value = payload.results ?? []
      fermiCount.value = payload.count ?? 0
      // Pagina oltre l'ultima: torna alla prima e ricarica.
      if (fermi.value.length === 0 && fermiCount.value > 0 && fermiPage.value > 1) {
        fermiPage.value = 1
        await fetchFermi(competenzaMese)
      }
    } finally {
      if (fvFermi.isCurrent(t)) fermiLoading.value = false
    }
  }

  // Scopo: azzera il drill-down (cambio mese/anno o deselezione card) e
  //        invalida le fetch fermi in volo.
  function resetFermi() {
    fvFermi.invalidate()
    areaSelezionata.value = null
    fermi.value = []
    fermiCount.value = 0
    fermiPage.value = 1
    fermiLoading.value = false
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped).
  function clearUserState() {
    fvMatrice.invalidate()
    anno.value = new Date().getFullYear()
    meseIdx.value = new Date().getMonth()
    mesi.value = []
    resetFermi()
  }

  return {
    anno,
    meseIdx,
    areaSelezionata,
    mesi,
    fermi,
    fermiCount,
    fermiPage,
    fermiPageSize,
    fermiLoading,
    fetchMatrice,
    fetchFermi,
    resetFermi,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (RLS/scope): reset al logout.
  userScoped: true,
})
