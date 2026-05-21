// Scopo: pattern di deferimento del contenuto pesante dei drawer alla fine
//   dell'animazione di slide PrimeVue. Evita il rimbalzo visivo dei
//   LookupSelect/AutoComplete/DatePicker che, montati durante l'animazione,
//   fanno percepire un "blocco e ripartenza" all'apertura.
//
// Pattern feedback_content_ready_after_show — adottato dai drawer pilota
// (ContrattoDrawer, PreventiviDrawer, ArticoloDrawer, ListinoDrawer,
// ConversioneUomDrawer) ed esteso ai drawer Tier 2 nel refactor UI 2026-05-22.
//
// Uso tipico:
//   const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
//
// Template:
//   <Drawer :visible="visible" @after-show="onAfterShow" ...>
//     <div class="app-drawer-content">
//       <template v-if="contentReady">
//         <!-- tutto il contenuto pesante (LookupSelect, AutoComplete, ecc.) -->
//       </template>
//     </div>
//   </Drawer>
//
// L'evento `after-show` di PrimeVue Drawer scatta a fine animazione slide
// (~280ms con la curva default); solo allora il composable porta contentReady
// a true e i child component pesanti vengono renderizzati.
//
// Il composable gestisce automaticamente il reset di contentReady a false
// alla chiusura del drawer: il chiamante NON deve aggiungere
// `contentReady.value = false` nel proprio watch su visible.

import { ref, watch } from 'vue'

// Scopo: ritorna stato + handler per il deferimento contenuto drawer.
//   `visibleSource` deve essere un getter reattivo (es. `() => props.visible`).
//   Il composable osserva la sorgente e azzera contentReady a ogni chiusura.
export function useDrawerContentReady(visibleSource) {
  const contentReady = ref(false)

  function onAfterShow() {
    contentReady.value = true
  }

  // Reset al close: necessario per riapertura pulita (contentReady ripartirebbe
  // da true se non resettato, vanificando il deferimento).
  watch(visibleSource, (val) => {
    if (!val) contentReady.value = false
  })

  return { contentReady, onAfterShow }
}
