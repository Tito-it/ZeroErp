// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le domande sulla veste d'accesso che il frontend fa ai dati del DB,
//        senza rifare le regole: lo stato lo dice `script.fn_stato_veste`, se
//        la veste apre la porta oggi lo dice `script.fn_veste_utilizzabile`.
// Note: ⭐ Sono due domande diverse e restano separate (D-G3-1 del
//       brief-db-accessi-area-clienti, 2026-11-27): lo stato e' il ciclo di vita
//       dell'invito e della revoca, `utilizzabile` e' la porta di oggi. Una
//       veste `ATTIVO` puo' non lasciar entrare (fuori dalle sue date, soggetto
//       spento, per l'operatore il rapporto chiuso).
// ------------------------------------------------------------
import { STATO_VESTE } from '../constants'

// Scopo: la veste e' accesa ma oggi non lascia entrare? Vero solo se il DB
//        dice `utilizzabile = false` di una veste `ATTIVO`: una veste spenta
//        non entra comunque, e lo dice gia' il suo stato. Un dato senza la
//        chiave (`utilizzabile` assente) non e' «ferma»: non si inventa un
//        rifiuto che il DB non ha dato.
export function vesteFermaOggi(veste) {
  return veste?.stato === STATO_VESTE.ATTIVO && veste?.utilizzabile === false
}
