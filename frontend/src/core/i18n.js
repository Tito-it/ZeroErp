// Istanza i18n centralizzata — importabile da router e altri moduli non-component.
// La locale attiva viene letta da localStorage all'init e persistita a ogni
// cambio tramite setAppLanguage(), in modo che sopravviva al reload.
//
// User-scoped: la preferenza lingua e' personale per utente (chiave
// `language_user_<id>` in localStorage). Al boot legge la chiave "device
// default"; dopo il login `syncUserLanguage(userId)` applica la preferenza
// personale. Evita che utente A (IT) imponga IT a utente B (EN) sullo
// stesso browser.
import { createI18n } from 'vue-i18n'
import { local, STORAGE_KEYS, userScopedKey } from './storage'
import { registerUserScopedResetter } from './pinia-plugins/auto-reset'

// Lingue UI supportate. Allineare con SUPPORTED_LANGUAGES del middleware BE
// (apps/core/middleware/user_language_middleware.py) e con le traduzioni
// popolate in config.messaggi_errore.
export const SUPPORTED_LOCALES = ['it', 'en']
export const DEFAULT_LOCALE = 'it'

// La locale `Intl` (BCP 47) di ogni lingua UI: quella che si passa a
// `toLocaleDateString` e `Intl.DateTimeFormat` per nomi di giorni e mesi.
// Estratta il 2026-10-09 (regola del 2, ok Tid): `AppTopbar` e `ProcessoDrawer`
// scrivevano ognuno `locale === 'it' ? 'it-IT' : 'en-GB'`. Una lingua nuova in
// `SUPPORTED_LOCALES` si aggiunge anche qui.
const _INTL_LOCALE = { it: 'it-IT', en: 'en-GB' }

/**
 * @param {string} lingua - lingua UI (`locale.value` di vue-i18n), es. 'it'
 * @returns {string} - es. 'it-IT'; la lingua di default se non e' nota
 */
export function intlLocale(lingua) {
  return _INTL_LOCALE[lingua] ?? _INTL_LOCALE[DEFAULT_LOCALE]
}

// userId corrente per la risoluzione delle chiavi user-scoped. Aggiornato
// da `syncUserLanguage(userId)` al login. Null = "device default".
let _currentUserId = null

function _readStoredLocale(userId) {
  const key = userScopedKey(STORAGE_KEYS.LANGUAGE, userId)
  const stored = local.get(key)
  if (stored && SUPPORTED_LOCALES.includes(stored)) return stored
  return null
}

function resolveInitialLocale() {
  // Al boot l'utente non e' ancora noto: leggi "device default".
  return _readStoredLocale(null) || DEFAULT_LOCALE
}

const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  // Le locale NON sono piu' bundlate inline: pesavano 262 KB raw / 65 KB
  // gzip (~20% del main chunk). Vengono caricate on-demand via
  // loadLocaleMessages() — solo la locale attiva al boot, l'altra allo
  // switch. Vedi docs/.../brief-fe-bundle-splitting.md.
  messages: {}
})

// Locale gia' caricate in memoria, per evitare re-import (idempotenza).
const _loadedLocales = new Set()

// Scopo: carica on-demand le traduzioni di una locale e le registra
//        nell'istanza i18n. Il dynamic import fa si' che Vite emetta un
//        chunk separato per ogni locale, fuori dal main bundle.
//        Idempotente: se gia' caricata, ritorna subito.
export async function loadLocaleMessages(locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return false
  if (_loadedLocales.has(locale)) return true
  const messages = await import(`../locales/${locale}.json`)
  i18n.global.setLocaleMessage(locale, messages.default)
  _loadedLocales.add(locale)
  return true
}

// Scopo: imposta la locale corrente di vue-i18n + persiste in localStorage.
//        Va invocata da qualunque componente che cambia lingua (es. switch
//        IT/EN in topbar); l'interceptor axios legge i18n.global.locale.value
//        per popolare l'header Accept-Language della request successiva.
//        Persiste in chiave user-scoped se loggato, altrimenti "device default".
export async function setAppLanguage(code) {
  if (!SUPPORTED_LOCALES.includes(code)) return false
  // Carica le traduzioni della locale target prima di attivarla, cosi'
  // lo switch non mostra le chiavi grezze nell'attesa del chunk.
  await loadLocaleMessages(code)
  i18n.global.locale.value = code
  const key = userScopedKey(STORAGE_KEYS.LANGUAGE, _currentUserId)
  local.set(key, code)
  // Hint per screen reader e browser nativi
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
  return true
}

// Scopo: sincronizza la lingua UI con la preferenza personale dell'utente
//        fornito. Chiamata da `auth.fetchProfile` dopo il login.
//
//        Precedenza lookup:
//          1) chiave user-scoped `language_user_<id>` → scelta personale
//          2) DEFAULT_LOCALE (fallback di prodotto)
//
//        NON si usa la chiave globale `language` come fallback: vedi
//        ui.js#syncUserPreferences per il razionale (chiave promiscua,
//        leak cross-user). La chiave globale resta per la pagina di
//        login pre-auth, non consultata nel sync utente.
export async function syncUserLanguage(userId) {
  _currentUserId = userId ?? null
  if (userId == null) return
  const resolved = _readStoredLocale(userId) || DEFAULT_LOCALE
  await loadLocaleMessages(resolved)
  i18n.global.locale.value = resolved
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', resolved)
  }
}

// Scopo: azzera lo scope utente corrente (chiamata dal logout centralizzato
//        tramite `registerUserScopedResetter`). Non cambia la lingua UI
//        corrente — la lascia al valore attuale come "device default" per
//        la pagina di login e l'eventuale prossimo utente senza preferenza.
export function clearUserLanguageScope() {
  _currentUserId = null
}

// Applica lang attribute al mount (senza aspettare un cambio utente)
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', i18n.global.locale.value)
}

// Al logout azzera lo scope utente: la lingua UI corrente resta per la
// pagina di login (non ha senso forzare un cambio testuale istantaneo),
// ma il prossimo `setAppLanguage` scrivera' sul "device default" fino
// al prossimo `syncUserLanguage`.
registerUserScopedResetter(clearUserLanguageScope)

export default i18n
