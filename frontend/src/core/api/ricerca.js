// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API della RICERCA UNIVERSALE dei soggetti (drawer di ricerca della
//        topbar): i tipi ruolo cercabili, la ricerca vera e propria e il
//        dettaglio di una riga espansa.
// ------------------------------------------------------------
import api from '../api'

// Scopo: i tipi ruolo che il catalogo dichiara visibili nella ricerca.
export function lookupTipiRuoloRicerca() {
  return api.get('/core/lookup/tipi-ruoli/', { params: { ricerca_visibile: true } })
}

// Scopo: cerca i soggetti per termine e tipo ruolo, paginato.
export function ricercaSoggetti(params) {
  return api.get('/core/search/', { params })
}

// Scopo: dettaglio di un soggetto per tipo ruolo (row expansion della ricerca).
export function dettaglioRicercaSoggetto(soggettoId, params) {
  return api.get(`/core/search/${soggettoId}/detail/`, { params })
}
