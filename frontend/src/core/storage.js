// Layer unico per accesso localStorage/sessionStorage.
// Centralizza chiavi e operazioni — nessun modulo deve accedere direttamente a storage.

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  // §8.5.2: key del canale di login corrente (CANALE_LOGIN.{ADMIN,PORTALE,SHOP}).
  // Persistita per consentire al refresh token di usare l'endpoint giusto
  // dopo un page reload, senza dover decodificare il JWT lato client.
  LOGIN_CHANNEL: 'login_channel',
  SIDEBAR_COLLAPSED: 'sidebar_collapsed',
  OPEN_TABS: 'open_tabs',
  DARK_MODE: 'dark_mode'
}

export function domainFavoriteKey(domainKey) {
  return `domain_default_${domainKey}`
}

export const local = {
  get(key) { return localStorage.getItem(key) },
  set(key, value) { localStorage.setItem(key, String(value)) },
  remove(key) { localStorage.removeItem(key) }
}

export const session = {
  get(key) { return sessionStorage.getItem(key) },
  set(key, value) { sessionStorage.setItem(key, String(value)) },
  remove(key) { sessionStorage.removeItem(key) }
}
