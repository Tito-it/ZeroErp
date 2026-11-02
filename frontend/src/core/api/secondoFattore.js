// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API del secondo fattore (TOTP) della PROPRIA credenziale: il secondo
//        passo del login e la configurazione (brief sicurezza §3.4-bis, T-4).
//        Le funzioni tornano la response axios: il chiamante decide come
//        mostrare l'esito.
// Note: il secondo passo apre la sessione (access nel corpo, refresh nel
//       cookie): lo chiama lo store auth, mai una view.
// ------------------------------------------------------------
import api from '../api'

// Scopo: il corpo della PROVA sul filo: `codice` (l'app di autenticazione)
//        OPPURE `codice_recupero`, mai entrambi. La prova arriva da
//        `utils/provaSecondoFattore` (`{ codice }` | `{ codiceRecupero }`).
// Note: unica sede della traduzione (regola del 2, 2026-10-02): la stessa
//       riga stava nel secondo passo e nella disattivazione.
function corpoProva({ codice, codiceRecupero }) {
  return codiceRecupero ? { codice_recupero: codiceRecupero } : { codice }
}

// Scopo: il secondo passo del login, sulla porta del canale. `prova` porta
//        `codice` (l'app di autenticazione) OPPURE `codiceRecupero`.
export function secondoPassoLogin(path, sfida, prova) {
  return api.post(path, { sfida, ...corpoProva(prova) })
}

const BASE = '/auth/secondo-fattore'

// Scopo: lo stato del proprio secondo fattore (device, obbligo e motivo,
//        codici di recupero rimasti).
export function getSecondoFattore() {
  return api.get(`${BASE}/`)
}

// Scopo: avvia (o ricomincia) la configurazione, dietro la password della
//        credenziale: QR, segreto e codici di recupero, che il backend dà UNA
//        volta sola.
export function registraSecondoFattore(password) {
  return api.post(`${BASE}/registra/`, { password })
}

// Scopo: chiude la configurazione col primo codice dell'app.
export function confermaSecondoFattore(codice) {
  return api.post(`${BASE}/conferma/`, { codice })
}

// Scopo: codici di recupero nuovi, dietro un codice dell'app.
export function rigeneraCodiciRecupero(codice) {
  return api.post(`${BASE}/codici-recupero/`, { codice })
}

// Scopo: disattiva il proprio secondo fattore, dietro un codice dell'app o un
//        codice di recupero.
export function disattivaSecondoFattore(prova) {
  return api.post(`${BASE}/disattiva/`, corpoProva(prova))
}
