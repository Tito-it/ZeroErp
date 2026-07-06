// Store Pinia Dashboard Fatturazione (brief-design-dashboard-fatturazione §7):
// anno, mese selezionato, matrice mensile e drill-down fermi.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (niente useApiHandler.execute su promise non-axios —
// memoria feedback_useapihandler_solo_axios).
// Il drill-down fermi usa il BB usePagedDashFetch (guard di versione +
// rientro pagina-oltre-l'ultima, estratto 2026-07-06 regola del 2);
// la matrice ha il suo guard di versione dedicato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
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
  const fvMatrice = useFetchVersion()

  // Drill-down fermi: sezione paginata standard.
  const fermiFetch = usePagedDashFetch((paging, competenzaMese) =>
    listDashboardFatturazioneFermi({
      competenza_mese: competenzaMese,
      area: areaSelezionata.value,
      ...paging,
    })
  )

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
  //        Senza area attiva non parte nessuna fetch.
  async function fetchFermi(competenzaMese) {
    if (!areaSelezionata.value) return
    await fermiFetch.fetch(competenzaMese)
  }

  // Scopo: azzera il drill-down (cambio mese/anno o deselezione card) e
  //        invalida le fetch fermi in volo.
  function resetFermi() {
    areaSelezionata.value = null
    fermiFetch.reset()
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped) —
  //        resetAll riporta anche la pageSize al default (stato utente).
  function clearUserState() {
    fvMatrice.invalidate()
    anno.value = new Date().getFullYear()
    meseIdx.value = new Date().getMonth()
    mesi.value = []
    areaSelezionata.value = null
    fermiFetch.resetAll()
  }

  return {
    anno,
    meseIdx,
    areaSelezionata,
    mesi,
    fermi: fermiFetch.items,
    fermiCount: fermiFetch.count,
    fermiPage: fermiFetch.page,
    fermiPageSize: fermiFetch.pageSize,
    fermiLoading: fermiFetch.loading,
    applyFermiPage: fermiFetch.applyPageEvent,
    fetchMatrice,
    fetchFermi,
    resetFermi,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (RLS/scope): reset al logout.
  userScoped: true,
})
