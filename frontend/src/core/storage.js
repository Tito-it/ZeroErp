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
  DARK_MODE: 'dark_mode',
  // Lingua UI preferita (codice ISO-2 minuscolo, es. 'it'|'en'). Persistita
  // in localStorage e riletta all'init di i18n.js; inviata al backend come
  // header HTTP Accept-Language (interceptor in core/api.js) per pilotare la
  // GUC myapp.user_language nei messaggi di errore DB.
  LANGUAGE: 'language'
}

export function domainFavoriteKey(domainKey) {
  return `domain_default_${domainKey}`
}

// Scopo: genera la chiave localStorage user-scoped per preferenze che
//        devono essere personali (tema dark/light, lingua UI). Se userId
//        e' null/undefined (pre-login o logout), usa la chiave "device
//        default" (STORAGE_KEYS.<BASE>) come fallback globale del browser.
//
//        Pattern: quando l'utente A loggato cambia tema, salviamo su
//        `<BASE>_user_<id>`; al login di B (stesso browser) leggiamo la
//        sua chiave personale, non quella di A. Se B non ha mai scelto,
//        eredita il "device default" come prima scelta ragionevole.
export function userScopedKey(baseKey, userId) {
  if (userId == null || userId === '') return baseKey
  return `${baseKey}_user_${userId}`
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
