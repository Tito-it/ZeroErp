// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API delle SESSIONI dell'operatore collegato (pannello «Sessioni
//        attive»): elenco e revoca, una o tutte le altre.
// ------------------------------------------------------------
import api from '../api'

// Scopo: le ALTRE sessioni aperte dell'operatore (esclusa la corrente), come
//        lista paginata (`core.sessioni_attive`): `params` porta ricerca,
//        ordinamento e pagina. La risposta ha anche `totale_attive`, le
//        sessioni a prescindere dalla ricerca.
export function listSessioni(params = {}) {
  return api.get('/core/me/sessioni/', { params })
}

// Scopo: revoca una sessione, per `jti` del suo refresh token.
export function revocaSessione(jti) {
  return api.post(`/core/me/sessioni/${jti}/revoca/`)
}

// Scopo: revoca tutte le sessioni tranne quella corrente. La risposta porta
//        `revoked`, quante ne ha chiuse.
export function revocaTutteSessioni() {
  return api.post('/core/me/sessioni/revoca-tutte/')
}
