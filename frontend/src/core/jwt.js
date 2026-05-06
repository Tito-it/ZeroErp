// Scopo: Helper JWT client-side puramente funzionali. NON validano la firma
// (responsabilita' del backend): servono solo per check di scadenza locale
// per evitare di fare chiamate inutili con token gia' morti e per decidere
// in router guard / interceptor se tentare un refresh proattivo.

// Decodifica il payload base64url di un JWT e ritorna `exp` in millisecondi
// (epoch). Ritorna null se token assente, mal formato o privo di `exp`.
export function decodeJwtExp(token) {
  if (!token || typeof token !== 'string') return null
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(b64))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

// True se token scaduto, mal formato o privo di `exp`. `leewayMs` permette
// di anticipare il giudizio (es. considerare scaduto 30s prima della reale
// scadenza per evitare race con clock skew).
export function isJwtExpired(token, leewayMs = 0) {
  const exp = decodeJwtExp(token)
  if (exp == null) return true
  return Date.now() + leewayMs >= exp
}
