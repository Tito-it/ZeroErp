// Layer unico per accesso localStorage/sessionStorage.
// Centralizza chiavi e operazioni — nessun modulo deve accedere direttamente a storage.

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
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
