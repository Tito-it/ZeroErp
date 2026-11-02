// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: client API pubblico dell'attivazione di una veste (operatore,
//   portale, shop): verifica del token e conferma. Una strada sola, come il
//   building block del backend (`apps/core/services/invito_veste.py`): fra le
//   porte cambiano solo gli endpoint e la sezione i18n.
// Note: endpoint pubblici (AllowAny), nessun JWT.
// ------------------------------------------------------------
import api from '../api'

// Scopo: Le porte d'attivazione. Specchio LEGITTIMO delle `PortaInvito` del
// backend: qui stanno solo le cose del frontend (URL, testi), la regola
// (quale flusso, quale veste) resta al backend. ⛔ Niente codici d'errore: la
// pagina non deduce dal codice, ri-verifica il token (AttivazioneVestePage).
export const PORTE_ATTIVAZIONE = Object.freeze({
  OPERATORE: Object.freeze({
    validatePath: (token) => `/auth/attivazione-validate/${token}/`,
    confermaPath: '/auth/attivazione/',
    i18n: 'auth'
  }),
  PORTALE: Object.freeze({
    validatePath: (token) => `/portale/attivazione/validate/${token}/`,
    confermaPath: '/portale/attivazione/conferma/',
    i18n: 'portale'
  }),
  SHOP: Object.freeze({
    validatePath: (token) => `/shop/attivazione/validate/${token}/`,
    confermaPath: '/shop/attivazione/conferma/',
    i18n: 'shop'
  })
})

// Scopo: Verifica il token senza consumarlo. Il BE risponde `valid`,
// `token_type` e `requires_password` (deciso sulla credenziale ADESSO).
export function validaTokenAttivazione(porta, token) {
  return api.get(porta.validatePath(token))
}

// Scopo: Conferma l'attivazione. Senza password da scegliere i campi non si
// mandano: il BE li ignorerebbe comunque, per non sovrascrivere la password
// che la persona usa gia'.
export function confermaAttivazione(porta, { token, newPassword, newPasswordConfirm }) {
  const payload = { token }
  if (newPassword) {
    payload.new_password = newPassword
    payload.new_password_confirm = newPasswordConfirm
  }
  return api.post(porta.confermaPath, payload)
}
