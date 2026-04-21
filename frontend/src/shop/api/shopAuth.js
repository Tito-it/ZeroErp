// Scopo: client API pubblico per attivazione account shop customer
// (B1 §13.7). Simmetrico a portale/api/portaleAuth.js, usa i tipi token
// shop (INVITO_SHOP / ATTIVAZIONE_SHOP_CROSS) e gli endpoint
// /api/v1/shop/attivazione/*. Non richiede JWT.
import api from '../../core/api'

// Scopo: Verifica se un token di attivazione shop e' ancora valido
// senza consumarlo. Il BE ritorna `token_type` e `requires_password`
// per guidare la UX:
//   INVITO_SHOP            -> form scelta password (primo accesso)
//   ATTIVAZIONE_SHOP_CROSS -> conferma one-click (password preesistente)
export function validateShopToken(token) {
  return api.get(`/shop/attivazione/validate/${token}/`)
}

// Scopo: Conferma attivazione shop. Il BE determina il flow dal
// token_type:
// - INVITO_SHOP: richiede `new_password` + `new_password_confirm`.
// - ATTIVAZIONE_SHOP_CROSS: password NON necessaria; se passata viene
//   ignorata dal BE come difesa.
// Il FE deve evitare di inviare password sui token CROSS per non
// generare rumore semantico nel payload.
export function attivaShop({ token, newPassword, newPasswordConfirm }) {
  const payload = { token }
  if (newPassword) {
    payload.new_password = newPassword
    payload.new_password_confirm = newPasswordConfirm
  }
  return api.post('/shop/attivazione/conferma/', payload)
}
