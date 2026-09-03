// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Client API dei REGISTRI DI NUMERAZIONE.
//
// ⚠️ LE ROTTE STANNO SOTTO `/vendite/`, LA MASCHERA VIVE IN AMMINISTRAZIONE, e
//    non e' un'incoerenza: il DATO e' di vendite (la tabella, i vincoli, le due
//    `fn_check_*`), il posto in cui si guarda e' il drawer dell'emittente
//    fiscale. Il permesso resta quello dell'area `vendite` — chi apre quel tab
//    senza il livello LETTURA su vendite non vede i registri, ed e' una
//    domanda di permessi, non un motivo per spostare il dominio dei dati.

import api from '../../core/api'

const BASE = '/vendite/registri'

// Scopo: lista paginata. ⛔ `attivo` si OMETTE per avere tutti: un registro
//        spento continua a occupare il suo slot, e una lista che di default
//        nasconde gli spenti nasconde proprio le righe che spiegano un rifiuto
//        in creazione.
export function listRegistri(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Scopo: dettaglio + i contatori (`progressivi`) in sola lettura.
export function getRegistro(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createRegistro(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateRegistro(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Scopo: accende o spegne il registro — verbo suo, non un PATCH su `attivo`.
// ⭐ E' anche il verbo della RIATTIVAZIONE: per una terna gia' occupata da un
//    registro spento non si crea, si riaccende quello che c'e' (§0 del brief).
export function setRegistroAttivo(id, attivo) {
  return api.post(`${BASE}/${id}/attivo/`, { attivo })
}
