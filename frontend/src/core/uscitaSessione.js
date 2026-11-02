// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: L'USCITA DALLA SESSIONE — chiudere una sessione morta e portare al
//        login col motivo. Separata da `core/api.js` il 2026-10-03: nessuna
//        delle due funzioni usa axios, e stando li' costringevano le viste che
//        le chiamano (cambio password, sicurezza) a importare il modulo del
//        client — la porta che `check-api-componenti` tiene chiusa ai
//        componenti. La usano l'interceptor di `core/api.js`, lo store `auth`
//        (logout da un'altra scheda) e le viste che chiedono una password
//        dentro la sessione.
// ⛔ Niente axios qui. Lo store `auth` si importa in modo DINAMICO (vedi sotto):
//    `stores/auth` importa `core/api`, che importa questo modulo.
// ------------------------------------------------------------

import { routerApp } from './routerApp'
import { MOTIVO_USCITA, azzeraAccess } from './sessione'
import { extractApiErrorCode } from './utils/apiError'

// Scopo: chiude la sessione morta e porta al login.
//
// 🔴 IL PUNTO CHE MANCAVA, ed è la causa del difetto «resto sulla home vuota e
//    al login ci arrivo solo ricaricando» (rilievo di Tid, 2026-09-04).
//    Lo stato di autenticazione viveva in DUE posti: `localStorage` e i ref
//    dello store Pinia, che dal localStorage erano stati letti UNA volta sola
//    alla creazione. Qui si ripuliva **solo il localStorage**, quindi lo store
//    continuava a tenere in memoria i due token. (Dal 2026-09-28 i token non
//    stanno più in localStorage: l'access vive solo in `core/sessione`.)
//    ⇒ `isAuthenticated` (che li legge dalla memoria e guarda solo la loro
//    SCADENZA) restava **vero**: una sessione uccisa dal server — refresh
//    blacklistato, identità revocata — ha token non ancora scaduti per data.
//    ⇒ Il `router.push` qui sotto finiva sul guard `if (to.name === 'login' &&
//    auth.isAuthenticated) return { name: 'home' }` e veniva **rimandato alla
//    home**. Da lì ogni chiamata rispondeva 401 e il login era irraggiungibile;
//    solo un ricarico — che rilegge il localStorage ormai vuoto — lo sbloccava.
// ⇒ Si azzera lo stato DOVE VIVE: `clearTokens()` dello store, che pulisce i
//    ref, il localStorage e gli store user-scoped (niente dati del vecchio
//    utente in memoria). Il localStorage lo tocca lui, non più questa funzione.
//
// ⚠️ Import DINAMICO, e non è un vezzo: `stores/auth` importa questo modulo
//    (e `api`, che lo importa a sua volta), quindi un import statico
//    chiuderebbe il ciclo uscitaSessione → auth → uscitaSessione. Qui lo store
//    serve solo a runtime, quando i moduli sono già valutati.
// ⚠️ Se l'import fallisse, si ripiega sul solo azzeramento dell'access in
//    memoria: meglio una sessione mezza chiusa che un'eccezione dentro un
//    interceptor, che si mangerebbe anche il redirect.
// Esportata: la usa anche lo store `auth` quando un'altra scheda chiude la
// sessione (logout), per arrivare al login per la stessa strada, col suo
// motivo (`MOTIVO_USCITA` in `core/sessione`).
export async function redirectToLogin(motivo = MOTIVO_USCITA.SESSIONE_SCADUTA) {
  try {
    const { useAuthStore } = await import('../stores/auth')
    useAuthStore().clearTokens()
  } catch {
    azzeraAccess()
  }
  // NB: LOGIN_CHANNEL non viene rimosso — conserva la preferenza utente
  // per il prossimo login manuale (stesso pattern di `clearTokens`).
  // Usa il router per evitare page reload; preserva la rotta per redirect post-login.
  // `reason=<motivo>` viene letto da LoginView per mostrare un messaggio
  // esplicito invece di una pagina muta (UX: l'utente capisce perché è
  // uscito e non pensa a un bug).
  const rottaCorrente = routerApp().currentRoute?.value
  // ⚠️ Se si e' gia' sul login non si spinge una seconda navigazione: con piu'
  //    chiamate in volo che prendono 401 insieme, ognuna passerebbe di qui e
  //    vue-router respingerebbe le repliche come «navigazione ridondante» —
  //    promise rifiutate che nessuno raccoglie, cioe' rumore in console su un
  //    percorso che sta gia' funzionando.
  if (rottaCorrente?.name === 'login') return

  const currentPath = rottaCorrente?.fullPath
  const query = { reason: motivo }
  if (currentPath && currentPath !== '/login') {
    query.redirect = currentPath
  }
  // ⚠️ `catch` sul push: una navigazione respinta da un guard (o superata da
  //    un'altra) rifiuta la promise, e qui dentro nessuno la aspetta.
  return routerApp().push({ name: 'login', query }).catch(() => {})
}

// Scopo: il freno della credenziale scattato su una password chiesta DENTRO
//        la sessione (cambio password, configurazione del secondo fattore):
//        il backend ha chiuso questa sessione, e si va al login col motivo.
//        true se era questo il caso; il chiamante, altrimenti, mostra l'errore.
// ⚠️ Solo `E_UTENTE_BLOCCATO`: e' il solo freno che chiude la sessione
//    (`password_con_freno.py`). `E_LOGIN_ATTESA` rallenta e basta.
export function seSessioneChiusaDalFreno(err) {
  if (extractApiErrorCode(err) !== 'E_UTENTE_BLOCCATO') return false
  redirectToLogin(MOTIVO_USCITA.FRENO_PASSWORD)
  return true
}
