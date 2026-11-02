// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la TESTATA DEI PRESIDI — {totale, con_righe, non_letti} — per il
//        pallino della topbar (`usePresidiPolling`). E' infrastruttura
//        (`dbops.presidi`), non una schermata di amministrazione: per questo
//        l'URL sta in `core/api/`, anche se l'endpoint lo serve `amm_software`.
// Note: il pannello «Processi automatici» legge presidi e righe con la sua
//       funzione (`getProcessiPresidi`, in amministrazione) e passa la testata
//       al pallino con `adottaTestataPresidi`.
// ------------------------------------------------------------
import api from '../api'

// Scopo: la sola testata, senza le prime righe: la legge ogni scheda aperta,
//        a cadenza lenta.
export function getPresidiConteggi() {
  return api.get('/amm-software/processi/presidi/conteggi/')
}
