// Scopo: building block stato per il tab "Revisioni" dei drawer documento
// (offerte commerciali, preventivi, future entita' con catena revisioni).
//
// Estrazione voluta dalla regola del 2 (`feedback_regola_del_2_estrai_bb`)
// alla seconda occorrenza identica tra OffertaDrawer e PreventiviDrawer:
// stesso state (`activeTab`, `revisioni`), stesso reset all'apertura,
// stessa chiamata di load con guard di versione anti-race.
//
// VERSIONE CAUTA (decisa con Tid 2026-05-28): SOLO state + load + reset.
// NIENTE componente template condiviso, niente auto-watch su visible/id.
// Il caller chiama esplicitamente `loadRevisioni(id)` dentro il suo
// `loadDetail` e `reset()` dentro il suo watch su `visible`. Cosi' i due
// drawer mantengono la liberta' di orchestrare il flusso come gia' fanno
// (es. OffertaDrawer carica revisioni dentro `loadOrReset`, PreventiviDrawer
// dentro `loadDetail` post-fetch detail).
//
// Uso tipico:
//
//   const tab = useRevisioniTab({
//     load: (id) => store.loadRevisioni(id),
//   })
//
//   async function loadDetail(id) {
//     const data = await store.fetchDetail(id)
//     ...
//     tab.loadRevisioni(id)            // best-effort + guard versione interno
//   }
//
//   watch(visible, v => {
//     if (!v) tab.reset()              // chiusura: invalida + svuota
//     else { tab.reset(); /* poi loadDetail */ }
//   })
//
//   // Template:
//   <Tabs v-model:value="tab.activeTab.value">
//     <TabPanel value="testata">...</TabPanel>
//     <TabPanel value="revisioni">
//       <span v-if="tab.revisioni.value.length">({{ tab.revisioni.value.length }})</span>
//       <DataTable :value="tab.revisioni.value" ...>...</DataTable>
//     </TabPanel>
//   </Tabs>
//
// Il guard di race usa `useFetchVersion`: una risposta arrivata dopo un
// `reset()` o un nuovo `loadRevisioni()` viene scartata invece di
// sovrascrivere lo stato.

import { ref } from 'vue'
import { useFetchVersion } from './useFetchVersion'

export function useRevisioniTab({ load }) {
  const activeTab = ref('testata')
  const revisioni = ref([])
  const fv = useFetchVersion()

  // Scopo: carica la catena revisioni per il documento `id`. Best-effort:
  // un fail lascia l'array vuoto (il template mostra "empty state").
  // Guard di versione: risposte stantii vengono scartate.
  async function loadRevisioni(id) {
    if (!id) {
      revisioni.value = []
      return
    }
    const t = fv.tag()
    try {
      const list = await load(id)
      if (fv.isCurrent(t)) revisioni.value = list || []
    } catch {
      if (fv.isCurrent(t)) revisioni.value = []
    }
  }

  // Scopo: reset all'apertura/chiusura del drawer. Invalida load in volo
  // (`fv.invalidate`) → eventuali risposte ritardate non sovrascrivono lo
  // stato fresco. Reset esplicito di `activeTab` a "testata" per evitare
  // che il tab attivo della scorsa apertura sopravviva al cambio entita'.
  function reset() {
    activeTab.value = 'testata'
    revisioni.value = []
    fv.invalidate()
  }

  return {
    activeTab,
    revisioni,
    loadRevisioni,
    reset,
  }
}
