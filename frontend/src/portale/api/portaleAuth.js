// Scopo: client API pubblico per attivazione account portale.
// Non richiede JWT. Usa l'istanza axios condivisa con baseURL `/api/v1/`
// (il token JWT se presente e' ignorato lato BE — endpoint AllowAny).
import api from '../../core/api'

// Scopo: Verifica se un token INVITO_PORTALE e' ancora valido senza consumarlo.
// Usato dalla pagina attivazione per mostrare form o messaggio scaduto.
export function validateInvitoPortaleToken(token) {
  return api.get(`/portale/attivazione/validate/${token}/`)
}

// Scopo: Conferma attivazione portale: consuma token + imposta password.
// L'utente dovra' poi fare login esplicito con la nuova password.
export function attivaPortale({ token, newPassword, newPasswordConfirm }) {
  return api.post('/portale/attivazione/conferma/', {
    token,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}
