// Scopo: client API per il profilo portale (namespace autenticato
// /api/v1/portale/profile/*). Usa l'istanza axios condivisa, che aggiunge
// automaticamente il JWT e gestisce il refresh.

import api from '../../core/api'

// Scopo: Attiva la veste SHOP_CUSTOMER per l'utente portale corrente
// (B1 §13.7). Endpoint reale post-fix resolver multi-veste: crea
// l'identita SHOP_CUSTOMER sullo stesso `soggetto_ruolo` della veste
// portale corrente, immediatamente attiva (no email/token: il consenso
// e' implicito nel click). Idempotente lato BE: chiamate ripetute
// ritornano `already_active: true`.
//
// Risposta 200 con `data: { activated|already_active, identita_id, message }`.
// Errori specifici lato BE:
//   - E_ATTIVAZIONE_SHOP_CROSS 400: ruolo non CLIENTE_PORTALE, GUC vuota,
//     identita esistente collegata ad altro auth_user (anti-tampering).
//
// `Idempotency-Key`: la mette l'interceptor di `core/api.js`, come su ogni
// POST che scrive.
export function attivaAccessoShop() {
  return api.post('/portale/profile/activate-shop/')
}
