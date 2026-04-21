// Scopo: client API pubblico per attivazione account portale.
// Non richiede JWT. Usa l'istanza axios condivisa con baseURL `/api/v1/`
// (il token JWT se presente e' ignorato lato BE — endpoint AllowAny).
import api from '../../core/api'

// Scopo: Verifica se un token di attivazione portale e' ancora valido
// senza consumarlo. Post §8.4.2 il BE ritorna anche `token_type` e
// `requires_password` per guidare la UX (INVITO → form password,
// CROSS → conferma one-click).
export function validateInvitoPortaleToken(token) {
  return api.get(`/portale/attivazione/validate/${token}/`)
}

// Scopo: Conferma attivazione portale (§8.4.2). Il BE determina il
// flow dal token_type:
// - INVITO_PORTALE: richiede `new_password` + `new_password_confirm`
//   (l'utente sceglie la password al primo accesso).
// - ATTIVAZIONE_PORTALE_CROSS: password NON necessaria (l'utente ha
//   gia' le credenziali da un'altra veste); se passata viene ignorata
//   dal BE come difesa.
// Il FE deve evitare di inviare password quando il token e' CROSS per
// non generare rumore semantico nel payload.
export function attivaPortale({ token, newPassword, newPasswordConfirm }) {
  const payload = { token }
  if (newPassword) {
    payload.new_password = newPassword
    payload.new_password_confirm = newPasswordConfirm
  }
  return api.post('/portale/attivazione/conferma/', payload)
}
