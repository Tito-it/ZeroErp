// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API della PASSWORD dell'operatore: cambio (sessione aperta) e
//        recupero (pagine pubbliche, senza JWT). Le funzioni tornano la
//        response axios: il chiamante decide come mostrare l'esito.
// Note: il cambio password restituisce token NUOVI; li salva lo store auth
//       (`cambiaPassword`), mai la view.
// ------------------------------------------------------------
import api from '../api'

// Scopo: cambia la password dell'operatore collegato.
export function cambiaPassword({ oldPassword, newPassword, newPasswordConfirm }) {
  return api.post('/auth/change-password/', {
    old_password: oldPassword,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}

// Scopo: chiede l'email di recupero per un nome utente o un'email (endpoint
//        pubblico, L-4): il backend cerca prima l'email, poi il nome utente.
export function richiediResetPassword(identificativo) {
  return api.post('/auth/password-reset-request/', { identificativo })
}

// Scopo: verifica, senza consumarlo, il token di recupero ricevuto via email.
export function validaTokenResetPassword(token) {
  return api.get(`/auth/password-reset-validate/${token}/`)
}

// Scopo: imposta la nuova password con il token di recupero.
export function confermaResetPassword({ token, newPassword, newPasswordConfirm }) {
  return api.post('/auth/password-reset-confirm/', {
    token,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}
