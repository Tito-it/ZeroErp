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
  //
  // ⛔ IL RESET STA QUI, SULLA SORGENTE, E NON SU `@after-hide`. La domanda
  //    torna, perche' la soluzione «ovvia» sembra migliore: azzerando a fine
  //    animazione di USCITA il contenuto resterebbe visibile per tutto lo
  //    slide-out, invece di sparire di colpo lasciando scivolare via un
  //    pannello vuoto. E' vero, ed e' un guadagno di un quarto di secondo —
  //    ma si paga con due difetti FUNZIONALI, non cosmetici:
  //
  //    1. CHIUDI E RIAPRI IN FRETTA. L'animazione di uscita viene interrotta
  //       da quella di entrata. Se `after-hide` arriva comunque, arriva DOPO
  //       l'`after-show` della riapertura: `contentReady` torna false a drawer
  //       APERTO, e l'utente si trova un pannello vuoto da cui esce solo
  //       richiudendo e riaprendo. Con il watch sulla sorgente l'ordine e'
  //       determinato e il caso non esiste.
  //    2. UNA CHIUSURA CHE NON EMETTE L'EVENTO (animazione disabilitata,
  //       chiusura programmatica, casi limite del componente) lascia il
  //       cancello APERTO: alla riapertura il contenuto si monta durante lo
  //       slide-in e il rimbalzo torna — in silenzio, che e' il modo peggiore.
  //
  //    ⇒ Si scambierebbe un difetto estetico CERTO con due difetti possibili.
  //    ⚠️ E la variante «una riga» non esiste: `@after-hide` e' un attributo
  //       del template, quindi andrebbe aggiunto in ~64 drawer, uno per uno.
  //    ℹ️ Valutato e scartato il 2026-09-05. Se qualcuno ci ripensa: la
  //       decisione e' questa, e va cambiata QUI per tutti — mai su un drawer
  //       solo, o le due meta' dell'applicazione si comportano diversamente.
  watch(visibleSource, (val) => {
    if (!val) contentReady.value = false
  })

  return { contentReady, onAfterShow }
}
