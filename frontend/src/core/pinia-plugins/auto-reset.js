// Scopo: Plugin Pinia che automatizza il reset degli store "user-scoped" al
//        logout. Risolve il rischio di data leak cross-user sullo stesso
//        browser — ogni store che contiene dati dell'utente loggato deve
//        essere azzerato alla chiusura sessione.
//
//        Contratto d'uso — uno store si dichiara user-scoped nel terzo
//        parametro di `defineStore`:
//
//            export const useMioStore = defineStore(
//              'mio',
//              () => { ... },
//              { userScoped: true }
//            )
//
//        Il plugin intercetta la creazione dello store e:
//          1) prende uno snapshot dello state iniziale (pre-login);
//          2) espone `$resetToInitial()` che ripristina quello snapshot.
//
//        Se lo store definisce un'action `clearUserState()` (tipicamente
//        perche' deve pulire side-effect come localStorage), il reset
//        centralizzato la preferisce a `$resetToInitial()`.
//
//        L'helper `resetAllUserScopedStores()` itera tutti gli store user-
//        scoped istanziati e fa il reset. E' la funzione che il logout
//        chiama al posto delle N cleanup manuali di prima.
//
//        Nota importante: lo snapshot usa `JSON.parse(JSON.stringify(...))`
//        — gli state degli store user-scoped devono essere JSON-serializable
//        (primitives, oggetti/array piani). Niente Map/Set/Date/function
//        nello state; se servono, esporre `clearUserState()` custom.

import { getActivePinia } from 'pinia'

// Registro degli store user-scoped istanziati, una entry per istanza di Pinia.
//
// Perche' un registro nostro e non `pinia._s`: quella e' la mappa interna di
// Pinia (API privata, nessuna garanzia di stabilita' fra major). Il plugin
// vede gia' ogni store al momento della creazione, quindi il registro lo
// costruiamo noi con sola API pubblica e restiamo indipendenti dagli interni
// della libreria. Il sintomo di una rottura li' sarebbe silenzioso — l'utente
// B che vede i dati dell'utente A — e nessun test lo intercetterebbe.
//
// WeakMap sull'istanza di Pinia (non un Set globale): in HMR e nei test si
// creano piu' istanze, e gli store della vecchia non devono sopravvivere
// nella nuova.
const _userScopedStores = new WeakMap()

// Scopo: aggiunge `$resetToInitial()`, marca lo store come user-scoped e lo
//        iscrive al registro di reset.
//        Funzione di registrazione da passare a `pinia.use(autoResetPlugin)`
//        in `main.js`.
export function autoResetPlugin({ pinia, store, options }) {
  if (!options?.userScoped) return

  // Snapshot dello state al momento della creazione dello store.
  // Pinia istanzia lo store la prima volta che `useXxxStore()` viene
  // chiamato — quindi lo snapshot riflette lo state subito dopo
  // l'inizializzazione della factory, non lo state "pre-login".
  // Per store che leggono da localStorage all'init (es. `auth` legge
  // access_token), lo snapshot conterra' gia' i token se l'utente
  // ricarica la pagina da loggato. In quei casi lo store deve esporre
  // un'action `clearUserState()` esplicita che azzera davvero.
  const initial = JSON.parse(JSON.stringify(store.$state))

  // Marcatore diagnostico: non serve piu' a filtrare (ci pensa il registro),
  // ma rende riconoscibile uno store user-scoped nei Vue devtools.
  store.$isUserScoped = true
  store.$resetToInitial = () => {
    store.$patch(initial)
  }

  // Iscrizione al registro dell'istanza di Pinia corrente.
  let registry = _userScopedStores.get(pinia)
  if (!registry) {
    registry = new Set()
    _userScopedStores.set(pinia, registry)
  }
  registry.add(store)

  // Uno store distrutto esce dal registro: `$dispose()` e' API pubblica, e
  // senza questo il registro terrebbe in vita store morti (oggi nessuno lo
  // chiama, ma il costo di tenerlo onesto e' tre righe).
  const dispose = store.$dispose.bind(store)
  store.$dispose = () => {
    registry.delete(store)
    dispose()
  }
}

// Registro di resetter per state module-scope che NON sta in Pinia (es.
// cache dentro composable: `useGlobalLookup._cache`, `useTabEvents.listeners`).
// Ogni modulo che mantiene state condiviso user-scoped si registra una volta
// al top-level; al logout il registro viene iterato insieme agli store Pinia.
const _moduleResetters = new Set()

// Scopo: registra una funzione di reset per state module-scope (non Pinia).
//        Chiamata dai composable che tengono cache condivise tra istanze.
//        Idempotente: una stessa funzione registrata piu' volte vale una.
//
//        Esempio:
//          // dentro un composable, al top-level:
//          registerUserScopedResetter(() => _cache.clear())
//
//        Non ritorna un dispose: questi resetter vivono quanto il modulo
//        stesso (tutta la durata del processo del browser-tab), non serve
//        deregistrarli.
export function registerUserScopedResetter(fn) {
  if (typeof fn === 'function') {
    _moduleResetters.add(fn)
  }
}

// Scopo: resetta tutto lo state user-scoped: store Pinia + module-scope
//        registrati. Chiamata dal flow di logout in `stores/auth.js`.
//
//        Ordine di preferenza per ogni store:
//          1) se espone `clearUserState`: la invoca (puo' pulire storage
//             o fare altro lavoro che snapshot non copre);
//          2) altrimenti fallback su `$resetToInitial()` dal plugin.
//
//        Dopo gli store, esegue tutti i resetter module-scope registrati.
export function resetAllUserScopedStores() {
  const pinia = getActivePinia()
  const registry = pinia ? _userScopedStores.get(pinia) : null
  if (registry) {
    for (const store of registry) {
      if (typeof store.clearUserState === 'function') {
        store.clearUserState()
      } else if (typeof store.$resetToInitial === 'function') {
        store.$resetToInitial()
      }
    }
  }
  // Module-scope resetter (cache composable, ecc.). Best-effort: un
  // fallimento in uno non blocca gli altri.
  for (const fn of _moduleResetters) {
    try {
      fn()
    } catch (err) {
      console.warn('[auto-reset] module resetter failed', err)
    }
  }
}
