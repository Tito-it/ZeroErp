// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ LE SCORCIATOIE DELLE AZIONI A VIDEO (2026-10-04, ok Tid). Un tasto
//        e' legato alla CHIAVE di un'azione, e agisce sull'unico componente
//        a video, al livello davanti, che ha quell'azione:
//          F2 Pulisci filtri · F4 Scarica lista · F5 Ricarica · F6 Nuovo
//          F8 Espandi/Comprimi tutte · F9 Personalizza colonne
//          Ctrl+S (⌘S su Mac) Salva
//        Si iscrivono `PageActionsBar` (le azioni della lista), `FiltriLista`
//        (F2) e `FormFooter` (Salva), che sono anche chi DICE il tasto nel
//        tooltip (`conTastoDiAzione`). Chi monta quei componenti non scrive
//        niente: ogni barra che ha l'azione ha anche il tasto.
//
// ⭐ PERCHE' TASTI F. Non dipendono dalla lingua (una lettera mnemonica in
//    italiano non lo e' in tedesco), continuano F5 e sono le convenzioni
//    AS/400 (F5 Aggiorna, F6 Crea). Esclusi quelli che il browser si tiene:
//    F1 guida, F3 trova, F7 cursore, F10 menu, F11 schermo intero, F12
//    strumenti. ⚠️ Con F2 i tasti F sicuri sono finiti: il prossimo comando
//    vuole un'altra forma, non un F rubato al browser.
//
// 🔴 I DIFETTI CHE QUESTA SEDE CHIUDE. Ogni scorciatoia era un listener su
//    `window` per COMPONENTE, tolto solo allo smontaggio:
//    · F5 (`useSearchTable`): sotto KeepAlive una lista non si smonta mai, e
//      ogni F5 ricaricava TUTTE le liste gia' visitate;
//    · Ctrl+S (`FormFooter`): con un drawer aperto sopra un altro, o un dialog
//      sopra un drawer, Ctrl+S salvava TUTTI i form montati — il template e
//      la sua versione insieme.
//
// ⭐ LA REGOLA. Un listener solo. Un tasto agisce sull'UNICO iscritto che:
//    · e' a video (nel documento e visibile: una tab in KeepAlive o una
//      scheda nascosta non lo sono);
//    · sta al livello DAVANTI (`livelloDavanti`): il dialog in cima se ce n'e'
//      uno aperto, altrimenti il drawer in cima (`DRAWER_IN_CIMA_KEY` da
//      `AppDrawer`), altrimenti la pagina;
//    · ha quell'azione visibile.
//    ⛔ Due iscritti candidati = il tasto non fa niente: un tasto ambiguo non
//    sceglie a caso. Un'azione visibile ma SPENTA ingoia il tasto e non
//    esegue, come il suo pulsante.
// ⚠️ F5 e Ctrl+S si ingoiano SEMPRE quando c'e' un iscritto a video, anche se
//    non eseguono: altrimenti il browser ricaricherebbe l'applicazione, o
//    aprirebbe «Salva pagina con nome», sopra un lavoro aperto.

import { getCurrentInstance, inject, onMounted, onUnmounted } from 'vue'
import { DRAWER_IN_CIMA_KEY, drawerAperti } from './useDrawerInCima'
import { dialogInCima } from '../utils/escapeSoloInCima'
import { TASTO, conScorciatoia } from '../utils/scorciatoie'

// Chiave dell'azione -> tasto (un codice di `TASTO`, `scorciatoie.js`).
export const SCORCIATOIE = Object.freeze({
  'pulisci-filtri': TASTO.F2,
  export: TASTO.F4,
  reload: TASTO.F5,
  new: TASTO.F6,
  'espandi-tutte': TASTO.F8,
  'personalizza-colonne': TASTO.F9,
  salva: TASTO.SALVA,
})

// I tasti che il browser userebbe per qualcosa di distruttivo: si ingoiano
// sempre sotto un iscritto a video.
const SEMPRE_INGOIATI = new Set([TASTO.F5, TASTO.SALVA])

const AZIONE_DEL_TASTO = Object.freeze(
  Object.fromEntries(Object.entries(SCORCIATOIE).map(([azione, tasto]) => [tasto, azione])),
)

// Scopo: il tasto di un'azione, o null.
export function tastoDiAzione(chiave) {
  return SCORCIATOIE[chiave] ?? null
}

// Scopo: l'etichetta di un'azione col suo tasto («Ricarica lista (F5)»), o
//        il testo com'e' se l'azione non ha tasto. Sede unica del tooltip con
//        la scorciatoia (barra, filtri, Salva).
export function conTastoDiAzione(t, te, testo, chiave) {
  const tasto = tastoDiAzione(chiave)
  return tasto && testo ? conScorciatoia(t, te, testo, tasto) : testo
}

// Scopo: il codice del tasto premuto (un valore di `TASTO`), o null. I tasti
//        F senza modificatori; il Salva con Ctrl o ⌘ e nient'altro. Con un
//        altro modificatore il tasto resta del browser (Ctrl+F5, Shift+F5).
export function codiceTasto(event) {
  const altri = event.altKey || event.shiftKey
  if (/^F\d{1,2}$/.test(event.key)) {
    return altri || event.ctrlKey || event.metaKey ? null : event.key
  }
  if ((event.ctrlKey || event.metaKey) && !altri && event.key?.toLowerCase() === 's') {
    return TASTO.SALVA
  }
  return null
}

// Scopo: l'elemento sta al livello davanti? Il dialog in cima vince su tutto;
//        senza dialog, il drawer in cima (`inCimaDrawer`, se l'elemento vive in
//        un drawer) o la pagina se nessun drawer e' aperto.
export function livelloDavanti(el, inCimaDrawer, { doc = document, aperti = drawerAperti } = {}) {
  const dialog = dialogInCima(doc)
  if (dialog) return Boolean(el && dialog.contains(el))
  return inCimaDrawer ? inCimaDrawer.value : aperti() === 0
}

const iscritti = new Set()
let installato = false

// Scopo: la regola, pura — quale iscritto esegue. `elenco` e' una lista di
//        { aVideo(), davanti(), azione(chiave) }; `azione` torna l'azione
//        VISIBILE con quella chiave, o null. Torna { iscritto, azione } o null.
export function scegliIscritto(elenco, chiave) {
  const candidati = []
  for (const i of elenco) {
    if (!i.aVideo() || !i.davanti()) continue
    const azione = i.azione(chiave)
    if (azione) candidati.push({ iscritto: i, azione })
  }
  return candidati.length === 1 ? candidati[0] : null
}

// Scopo: il gestore del tasto. `elenco` iniettabile per i test.
export function suTasto(event, { elenco = iscritti } = {}) {
  const codice = codiceTasto(event)
  const chiave = codice && AZIONE_DEL_TASTO[codice]
  if (!chiave) return false
  const aVideo = [...elenco].filter((i) => i.aVideo())
  if (!aVideo.length) return false
  if (SEMPRE_INGOIATI.has(codice)) event.preventDefault()
  if (event.repeat) return false
  const scelta = scegliIscritto(aVideo, chiave)
  if (!scelta) return false
  event.preventDefault()
  if (!scelta.iscritto.spenta(scelta.azione)) scelta.iscritto.esegui(scelta.azione)
  return true
}

function installa() {
  if (installato || typeof window === 'undefined') return
  window.addEventListener('keydown', (e) => suTasto(e))
  installato = true
}

// Scopo: iscrive un componente. `elemento()` la sua radice nel DOM,
//        `azioni()` le azioni VISIBILI ({ key, … }), `spenta(a)` e `esegui(a)`
//        quelle del suo pulsante (stesso motore del clic).
export function useScorciatoie({ elemento, azioni, spenta = () => false, esegui }) {
  const inCimaDrawer = getCurrentInstance() ? inject(DRAWER_IN_CIMA_KEY, null) : null
  const iscritto = {
    aVideo() {
      const el = elemento()
      return Boolean(el?.isConnected && el.offsetParent !== null)
    },
    davanti: () => livelloDavanti(elemento(), inCimaDrawer),
    azione: (chiave) => azioni().find((a) => a.key === chiave) ?? null,
    spenta,
    esegui,
  }
  onMounted(() => {
    installa()
    iscritti.add(iscritto)
  })
  onUnmounted(() => iscritti.delete(iscritto))
  return iscritto
}
