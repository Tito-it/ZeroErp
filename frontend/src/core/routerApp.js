// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL ROUTER DELL'APP, per chi sta in `core` (e negli store globali) e
//        deve navigare FUORI da un setup — l'interceptor HTTP che rimanda al
//        login, il bersaglio di un gesto, l'azione suggerita dall'assistente.
//        Dentro un componente si usa `useRouter()`.
//
// ⭐ Perche' non importare il modulo `router/`: il router e' la RADICE
//    dell'app, e per mestiere nomina tutti i domini (le loro view, i loro
//    vocabolari). Importarne il modulo da `core` era una dipendenza
//    core → dominio passata dalla porta di servizio (frontend-standards
//    §«Confini fra domini», 2026-09-26). Qui `core` riceve l'ISTANZA:
//    `main.js` la consegna all'avvio, prima del mount.
// ⛔ Chiedere il router prima della consegna e' un ERRORE, non un `null`:
//    una navigazione che non parte in silenzio e' il difetto peggiore.
// ------------------------------------------------------------

let istanza = null

// Scopo: consegna l'istanza del router (una volta, da `main.js`).
export function registraRouter(router) {
  istanza = router
}

// Scopo: l'istanza del router dell'app.
export function routerApp() {
  if (!istanza) throw new Error('routerApp: router non ancora registrato (main.js)')
  return istanza
}
