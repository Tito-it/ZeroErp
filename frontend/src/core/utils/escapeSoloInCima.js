// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
//    sempre. ⏳ Due drawer impilati si chiudono ancora insieme (stesso difetto
//    di PrimeVue): fuori perimetro qui, e' il chrome del drawer.

// La maschera di ogni `Dialog` PrimeVue aperto (AppDialog e ConfirmDialog):
// c'e' finche' il dialog e' montato, transizione di uscita compresa.
const MASCHERA_DIALOG = '.p-dialog-mask'

// Scopo: la regola, pura — vero se l'ESC e' stato ingoiato. Separata
//        dall'installazione per poterla provare senza DOM.
export function escapeSoloInCima(event, doc) {
  if (event.code !== 'Escape') return false
  if (!doc.querySelector(MASCHERA_DIALOG)) return false
  event.stopImmediatePropagation()
  return true
}

// Scopo: aggancia la regola a `document`, UNA volta, all'avvio dell'app.
//        Torna la funzione che la sgancia (per i test e per simmetria).
export function installaEscapeSoloInCima(doc = document) {
  const listener = (event) => escapeSoloInCima(event, doc)
  doc.addEventListener('keydown', listener)
  return () => doc.removeEventListener('keydown', listener)
}
