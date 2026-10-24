// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'IMPALCATURA per montare un componente in un test — i plugin che
//        `main.js` installa sull'app vera (Pinia, PrimeVue, vue-i18n, la
//        direttiva tooltip), messi in un posto solo perche' un componente
//        senza di loro non si monta e basta.
//
// ⭐ Nasce col PRIMO test di componente del progetto (2026-09-23,
//    `DrawerActionsBar.spec.js`). Fino a quel giorno i test provavano solo
//    funzioni pure e nessuno montava niente: `@vue/test-utils` e `jsdom` sono
//    entrati quel giorno, con l'ok di Tid, dopo che TRE cantieri in una
//    settimana avevano lasciato scoperto lo stesso difetto.
//
// ⛔ VIVE FUORI DA `src/`, ed e' una scelta: non e' codice applicativo, non
//    deve finire in nessun bundle e non deve comparire in un catalogo di
//    building block. Un file di test dentro `src/` prima o poi qualcuno lo
//    importa dall'applicazione.
//
// ⚠️ Chi lo usa deve dichiarare il DOM nel proprio file:
//        // @vitest-environment jsdom
//    in cima, prima di tutto. L'ambiente di default resta node (vite.config.js):
//    e' la riga che dice, leggendo il file, che quel test tocca il DOM.
//
// ⭐ La regola che tiene in piedi questo modulo: **si monta il componente
//    vero, si fingono solo i suoi CONTORNI**. Un test che sostituisce il
//    componente sotto esame con un finto prova il finto.
// ------------------------------------------------------------

import { mount } from '@vue/test-utils'
import { afterEach } from 'vitest'
import { createPinia, getActivePinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import { createI18n } from 'vue-i18n'

// ⚠️ `window.matchMedia` NON ESISTE in jsdom, e non e' un difetto del
//    progetto: jsdom non implementa il CSS, quindi non ha nulla da
//    interrogare. PrimeVue lo chiama (il `Select` del paginator lo usa per
//    l'orientamento) e senza muore con «matchMedia is not a function».
// ⭐ Qui si colma la LACUNA DELL'AMBIENTE, non si finge un pezzo del
//    componente: torna sempre «non corrisponde», che e' la risposta onesta —
//    in jsdom nessuna media query corrisponde a niente.
// ⛔ Corollario, e vale per ogni test di componente: **le media query qui non
//    si provano**. La variante compatta di una barra o di una toolbar sotto i
//    1024px e' CSS, e resta materia di collaudo a video.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })
}

// ⚠️ Stessa lacuna, stessa cura: `ResizeObserver` NON ESISTE in jsdom (niente
//    layout, niente da misurare). Il `Textarea` di PrimeVue con `auto-resize`
//    lo crea al montaggio — `MotivoDialog` e chi lo usa — e senza muore con
//    «ResizeObserver is not defined». Un osservatore che non osserva niente e'
//    la risposta onesta: in jsdom le dimensioni non cambiano mai.
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

// Scopo: l'i18n dei test — `t` rende la CHIAVE, non una frase.
// ⭐ Cosi' le asserzioni parlano di chiavi: le frasi vivono nei `locales`, si
//    riscrivono quando cambia il tono, e un test che le pinna diventa rosso
//    per una virgola. La chiave invece e' il contratto.
// ⚠️ `missingWarn` spento: qui la chiave mancante e' la norma, non un difetto
//    — il messaggio a video lo presidia `check_i18n_keys.py`, non questo.
function i18nDiProva(messages = {}) {
  return createI18n({
    legacy: false,
    locale: 'it',
    fallbackLocale: 'it',
    missingWarn: false,
    fallbackWarn: false,
    // Senza messaggi `t('x.y')` torna 'x.y': e' esattamente cio' che serve.
    messages: { it: messages },
  })
}

// Scopo: monta un componente con i plugin che l'app vera installa.
//
//   componente — il componente sotto esame (quello VERO)
//   props      — le sue props
//   opts.slots     — gli slot che il chiamante passerebbe, per NOME. ⚠️ Stanno
//                    nella radice delle opzioni di `mount`, non dentro
//                    `global`: scritti li' verrebbero ignorati in SILENZIO, e
//                    il test proverebbe il componente senza il suo contenuto.
//                    ⭐ Per un building block contenitore non sono un
//                    dettaglio: `FiltriLista` decide COSA rendere guardando
//                    `$slots`, quindi senza slot non c'e' niente da provare.
//   opts.provide   — gli inject che il componente si aspetta dal padre
//                    (es. READONLY_KEY: la catena readonly dei drawer)
//   opts.messages  — messaggi i18n, quando un test vuole provare una frase
//   opts.global    — passato a `mount` cosi' com'e' (stubs, mocks, ...)
//
// ⚠️ LA PINIA E' QUELLA ATTIVA, non una nuova — e questa riga l'ha scritta un
//    test rosso, il primo giorno (test 7 di `DrawerActionsBar.spec.js`).
//    Montando con una Pinia propria, lo store che il TEST configura e quello
//    che il COMPONENTE legge sono due oggetti diversi: il permesso impostato
//    non arriva, e il test fallisce raccontando una cosa falsa («il pulsante
//    non compare col permesso»). ⇒ chi vuole preparare uno store fa
//    `setActivePinia(createPinia())` nel `beforeEach` e lo configura; qui si
//    riusa quella. Senza, se ne crea una e la si attiva, cosi' anche chi
//    chiama lo store DOPO il montaggio trova la stessa.
// ⚠️ Ogni componente montato si SMONTA a fine test, e non per pulizia: un
//    componente vivo tiene vivi i suoi timer, e un timer che scatta dopo la
//    fine del file trova jsdom gia' smontato. Il `TabList` di PrimeVue lo fa al
//    montaggio (`setTimeout` di 150 ms per la barra della scheda attiva, mai
//    cancellato): sull'ultimo test del file muore con «HTMLElement is not
//    defined», e Vitest lo conta come errore non gestito — CI rossa con tutti
//    i test verdi (`OperatoreDrawer.spec.js`, 2026-10-10).
// ⭐ Smontato, il timer scatta lo stesso ma trova i `$refs` vuoti ed esce
//    senza toccare il DOM. Il rimedio sta qui e non nel singolo spec: vale per
//    ogni componente che monta delle schede, e chi scrive il prossimo test non
//    deve saperlo.
// ⚠️ Chi smonta da se' (per provare lo smontaggio) resta libero di farlo: un
//    componente gia' smontato si salta.
const montati = new Set()
afterEach(() => {
  for (const wrapper of montati) {
    if (!wrapper.vm.$.isUnmounted) wrapper.unmount()
  }
  montati.clear()
})

export function monta(componente, props = {}, opts = {}) {
  // `attachTo`: per i test che guardano il FUOCO (`document.activeElement`),
  // che jsdom muove solo su elementi attaccati al documento.
  const { provide = {}, messages = {}, slots = {}, global = {}, attachTo } = opts
  let pinia = getActivePinia()
  if (!pinia) {
    pinia = createPinia()
    setActivePinia(pinia)
  }
  const wrapper = mount(componente, {
    props,
    slots,
    attachTo,
    global: {
      // ⚠️ I SERVIZI di PrimeVue stanno qui perche' `main.js` li installa
      //    sull'app vera, e un componente che chiama `useConfirm()` o
      //    `useToast()` senza di loro non si monta — muore con «No PrimeVue
      //    Confirmation provided». Non sono un dettaglio del test: sono un
      //    pezzo dell'impalcatura dell'applicazione, e il posto giusto per
      //    ricrearli e' questo, una volta per tutti.
      plugins: [pinia, PrimeVue, ConfirmationService, ToastService, i18nDiProva(messages)],
      directives: { tooltip: Tooltip },
      provide,
      ...global,
    },
  })
  montati.add(wrapper)
  return wrapper
}
