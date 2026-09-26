// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API delle SESSIONI dell'operatore collegato (pannello «Sessioni
//        attive»): elenco e revoca, una o tutte le altre.
// ------------------------------------------------------------
import api from '../api'

// Scopo: le sessioni aperte dell'operatore.
export function listSessioni() {
  return api.get('/core/me/sessioni/')
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
