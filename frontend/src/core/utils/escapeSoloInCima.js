// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: ⭐ ESC CHIUDE SOLO L'OVERLAY IN CIMA. In PrimeVue 4 `Dialog` e
//        `Drawer` registrano ciascuno un listener `keydown` su `document` e si
//        chiudono per conto proprio: un ESC dentro un dialog aperto da un
//        drawer chiudeva TUTTI E DUE (rilievo in-app di Tid, 2026-09-18, subito
//        dopo che la X era uscita dal chrome e ESC era diventata l'uscita da
//        tastiera).
//
// ⭐ COME. I listener sullo stesso nodo e nella stessa fase si eseguono in
//    ORDINE DI REGISTRAZIONE: questo si registra all'AVVIO (main.js), quindi
//    prima di qualunque Drawer/Dialog — che si agganciano quando si aprono — e
//    con `stopImmediatePropagation` li spegne tutti in un colpo QUANDO C'E' UN
//    DIALOG APERTO. Il dialog in cima ESC se lo gestisce da solo sulla propria
//    radice (`AppDialog`, e la `ConfirmDialog` in App.vue via `pt`), che sta
//    PRIMA di `document` nella risalita: la' ESC chiude quel dialog e basta.
//
// ⚠️ Fase bubble su `document`, NON capture: in capture l'evento non
//    arriverebbe nemmeno al bersaglio, e un `Select` aperto dentro il dialog
//    non chiuderebbe piu' la tendina con ESC. In bubble i componenti hanno gia'
//    fatto la loro parte quando arriviamo qui.
//
// ⚠️ Se il fuoco e' FUORI dal dialog (body, un pannello DatePicker teletrasportato
//    in body), la radice del dialog non vede l'ESC e qui si ingoia e basta:
//    non si chiude niente, che e' il comportamento sicuro. Il giro dopo, col
//    fuoco tornato nel dialog, ESC chiude il dialog.
//
// ⛔ Senza dialog aperti non si tocca niente: il Drawer si chiude con ESC come
//    sempre. Due drawer impilati li regola il chrome del drawer, con la stessa
//    idea: esce solo quello in cima (`useDrawerInCima`, in `AppDrawer`).

// La maschera di ogni `Dialog` PrimeVue aperto (AppDialog e ConfirmDialog):
// c'e' finche' il dialog e' montato, transizione di uscita compresa.
const MASCHERA_DIALOG = '.p-dialog-mask'

// Scopo: c'e' un dialog aperto?
export function dialogAperto(doc = document) {
  return Boolean(doc.querySelector(MASCHERA_DIALOG))
}

// Scopo: la maschera del dialog IN CIMA, o null. PrimeVue teletrasporta ogni
//        dialog in coda al `body` all'apertura: l'ultima maschera e' quella
//        davanti. La usano le scorciatoie (`useScorciatoie`): con un dialog
//        aperto agisce solo cio' che sta dentro di lui.
export function dialogInCima(doc = document) {
  const maschere = doc.querySelectorAll(MASCHERA_DIALOG)
  return maschere.length ? maschere[maschere.length - 1] : null
}

// Scopo: la regola, pura — vero se l'ESC e' stato ingoiato. Separata
//        dall'installazione per poterla provare senza DOM.
export function escapeSoloInCima(event, doc) {
  if (event.code !== 'Escape') return false
  if (!dialogAperto(doc)) return false
  event.stopImmediatePropagation()
  return true
}

// ⭐ ESC DA UNA TENDINA CHIUSA (2026-09-26, rilievo in-app di Tid: «ESC
//    bloccato se il fuoco e' su un campo»). Il `Select` di PrimeVue 4 fa
//    `stopPropagation` su ESC SEMPRE, anche a tendina chiusa (nel sorgente:
//    «@todo will be changed next versions»): scelto un valore, il fuoco resta
//    sulla tendina, e ESC non arriva piu' a `document` — il drawer non si
//    chiudeva e non chiedeva nemmeno delle modifiche non salvate.
//    MultiSelect e DatePicker lo fermano solo a pannello APERTO, com'e' giusto.
//
//    Rimedio, qui e non campo per campo: in CAPTURE (prima del Select) un ESC
//    su una tendina CHIUSA si toglie al Select — a tendina chiusa il suo ESC
//    non fa niente — e se ne rimanda una copia dal CONTENITORE della tendina,
//    che risale come avrebbe fatto l'originale: la radice di un `AppDialog`,
//    poi `document` (la regola qui sopra, poi Drawer e Dialog). A tendina
//    APERTA non si tocca: il primo ESC chiude la tendina, il secondo il resto.
const TENDINA = '.p-select'

// Scopo: la regola, pura. `crea` fabbrica la copia dell'evento (nei test un
//        oggetto finto: il progetto non ha jsdom).
export function escapeDaTendinaChiusa(event, crea = (init) => new KeyboardEvent('keydown', init)) {
  if (event.code !== 'Escape') return false
  const bersaglio = event.target
  const tendina = bersaglio?.closest?.(TENDINA)
  if (!tendina?.parentElement) return false
  // Il fuoco di un Select (etichetta o input) porta `aria-expanded`.
  if (bersaglio.getAttribute?.('aria-expanded') === 'true') return false
  event.stopImmediatePropagation()
  tendina.parentElement.dispatchEvent(
    crea({ key: 'Escape', code: 'Escape', bubbles: true, cancelable: true }),
  )
  return true
}

// Scopo: aggancia le due regole a `document`, UNA volta, all'avvio dell'app.
//        Torna la funzione che le sgancia (per i test e per simmetria).
export function installaEscapeSoloInCima(doc = document) {
  const listener = (event) => escapeSoloInCima(event, doc)
  const tendina = (event) => escapeDaTendinaChiusa(event)
  doc.addEventListener('keydown', listener)
  doc.addEventListener('keydown', tendina, true)
  return () => {
    doc.removeEventListener('keydown', listener)
    doc.removeEventListener('keydown', tendina, true)
  }
}
