// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La sessione JWT della scheda: l'access token SOLO IN MEMORIA e il
//        rinnovo coordinato fra le schede aperte (brief sicurezza §2, dal
//        2026-09-28).
//
//        Il refresh token non passa più di qui: sta in un cookie HttpOnly
//        che il JavaScript non vede (lo scrive e lo legge il backend). Un
//        script iniettato nella pagina non può leggerlo né spedirlo altrove,
//        e l'access in memoria vale al massimo 10 minuti.
//
// ⭐ PIÙ SCHEDE (decisione A di Tid, 2026-09-28: «le schede si mettono
//    d'accordo»). Ogni rinnovo ruota il refresh e mette in blacklist il
//    precedente: due schede che rinnovano nello stesso istante presenterebbero
//    lo stesso cookie, e la seconda verrebbe buttata fuori. Qui:
//    - il rinnovo gira dentro un lock del browser (`navigator.locks`), quindi
//      UNA scheda alla volta; il cookie è condiviso fra le schede, e chi entra
//      dopo usa già quello ruotato da chi è uscito;
//    - chi rinnova annuncia l'access nuovo sul `BroadcastChannel`, e le altre
//      schede lo prendono senza chiamare il backend;
//    - entrando nel lock si guarda se nel frattempo un'altra scheda ha già
//      portato un access valido: allora non si rinnova di nuovo.
//    ⚠️ Senza `navigator.locks` (browser vecchio, contesto non sicuro) il
//       rinnovo parte lo stesso, senza coordinamento: una scheda può uscire.
//
// ⛔ Niente axios e niente store qui: la chiamata HTTP del rinnovo la
//    passa `core/api.js` (`rinnovaAccess`), unico file che importa axios;
//    lo store `auth` si iscrive agli eventi delle altre schede. Così nessun
//    ciclo di import.
// ------------------------------------------------------------

import { ref } from 'vue'
import { isJwtExpired } from './jwt'

const NOME_CANALE = 'zeroerp-sessione'
const NOME_LOCK = 'zeroerp-rinnovo-sessione'
// Margine con cui un access «quasi scaduto» si considera già scaduto: evita
// di spedire un token che arriva morto al server per pochi secondi.
const MARGINE_SCADENZA_MS = 5_000

// Tipi dei messaggi fra schede.
export const EVENTO_SESSIONE = Object.freeze({
  // Un'altra scheda ha rinnovato: porta l'access nuovo.
  ACCESS: 'access',
  // Un'altra scheda ha chiuso la sessione (logout): il cookie non c'è più.
  LOGOUT: 'logout',
  // Un'altra scheda ha aperto una sessione DIVERSA (login, cambio emittente):
  // il cookie ora descrive un'altra sessione, e ciò che questa scheda mostra
  // non le appartiene più.
  SESSIONE_NUOVA: 'sessione_nuova'
})

// Perché la scheda torna al login: viaggia nella rotta (`?reason=`) e lo
// leggono il guard del router (una sessione dichiarata chiusa non rimbalza
// alla home) e `LoginView` (la frase). ⭐ Sede unica: un motivo nuovo si
// aggiunge QUI, con la sua chiave i18n in `FRASE_MOTIVO_USCITA`, e vale
// ovunque. I valori restano quelli già in uso nelle URL.
export const MOTIVO_USCITA = Object.freeze({
  // Il rinnovo è fallito: cookie assente, scaduto o revocato.
  SESSIONE_SCADUTA: 'session_expired',
  // Il logout l'ha fatto un'altra scheda dello stesso browser (dal
  // 2026-09-29: prima diceva «sessione scaduta», e non era vero).
  USCITA_ALTRA_SCHEDA: 'logout_other_tab',
  // Troppe password sbagliate chieste DENTRO la sessione (cambio password,
  // configurazione del secondo fattore): il backend ha chiuso questa sessione
  // (decisione A di Tid, 2026-10-03).
  FRENO_PASSWORD: 'password_attempts'
})

// Chiave i18n della frase di ogni motivo (`LoginView`).
export const FRASE_MOTIVO_USCITA = Object.freeze({
  [MOTIVO_USCITA.SESSIONE_SCADUTA]: 'auth.session_expired',
  [MOTIVO_USCITA.USCITA_ALTRA_SCHEDA]: 'auth.logout_other_tab',
  [MOTIVO_USCITA.FRENO_PASSWORD]: 'auth.sessione_chiusa_freno'
})

// Scopo: true se il motivo della rotta dice che è l'applicazione stessa ad
//        aver chiuso la sessione (qualunque motivo noto).
export function sessioneDichiarataChiusa(motivo) {
  return Object.values(MOTIVO_USCITA).includes(motivo)
}

// Reattivo: lo store `auth` ne deriva `isAuthenticated`.
const accessToken = ref(null)
let canale = null
let rinnovoInVolo = null
const iscritti = new Set()

// Scopo: il canale fra schede, creato alla prima necessità. Null dove
//        BroadcastChannel non esiste (test in node, browser vecchi).
function canaleSchede() {
  if (canale || typeof BroadcastChannel === 'undefined') return canale
  canale = new BroadcastChannel(NOME_CANALE)
  // Solo in node (i test): un canale aperto terrebbe vivo il processo. Il
  // browser non ha `unref` e non ne ha bisogno.
  canale.unref?.()
  canale.onmessage = ({ data }) => {
    if (!data?.tipo) return
    if (data.tipo === EVENTO_SESSIONE.ACCESS) {
      accessToken.value = data.token ?? null
      return
    }
    iscritti.forEach(fn => fn(data))
  }
  return canale
}

// Scopo: il ref dell'access (sola lettura per convenzione: si scrive con
//        `impostaAccess`/`azzeraAccess`).
export function accessTokenRef() {
  return accessToken
}

export function getAccessToken() {
  return accessToken.value
}

// Scopo: true se c'è un access non scaduto (con margine).
export function accessValido() {
  return !!accessToken.value && !isJwtExpired(accessToken.value, MARGINE_SCADENZA_MS)
}

// Scopo: tiene l'access in memoria e, salvo `annuncia: false`, lo passa alle
//        altre schede.
export function impostaAccess(token, { annuncia = true } = {}) {
  accessToken.value = token ?? null
  if (annuncia && token) annunciaAlleAltreSchede({ tipo: EVENTO_SESSIONE.ACCESS, token })
}

export function azzeraAccess() {
  accessToken.value = null
}

// Scopo: manda un evento alle altre schede (non a questa).
export function annunciaAlleAltreSchede(messaggio) {
  canaleSchede()?.postMessage(messaggio)
}

// Scopo: si iscrive agli eventi LOGOUT e SESSIONE_NUOVA delle altre schede.
//        Ritorna la funzione che toglie l'iscrizione.
export function suEventoAltraScheda(fn) {
  canaleSchede()
  iscritti.add(fn)
  return () => iscritti.delete(fn)
}

// Scopo: esegue `fn` col lock fra schede, o direttamente se il browser non
//        lo offre.
function conLock(fn) {
  if (typeof navigator !== 'undefined' && navigator.locks?.request) {
    return navigator.locks.request(NOME_LOCK, fn)
  }
  return fn()
}

// Scopo: rinnova l'access UNA volta per scheda e una scheda alla volta.
//        `rinnova` è la chiamata HTTP (in `core/api.js`) e ritorna l'access
//        nuovo; qui si decide QUANDO chiamarla. Chiamate concorrenti della
//        stessa scheda ricevono la stessa promise. Ritorna l'access valido,
//        o rifiuta se il rinnovo fallisce (sessione finita: si va al login).
export function rinnovaCoordinato(rinnova) {
  if (rinnovoInVolo) return rinnovoInVolo
  const tokenDiPartenza = accessToken.value
  rinnovoInVolo = Promise.resolve(conLock(async () => {
    // Un'altra scheda ha rinnovato mentre aspettavamo il lock: il suo
    // access è arrivato dal canale, non serve un secondo giro.
    if (accessToken.value && accessToken.value !== tokenDiPartenza && accessValido()) {
      return accessToken.value
    }
    const nuovo = await rinnova()
    // Una risposta senza access non e' un rinnovo riuscito: senza questo
    // controllo le richieste ripartirebbero con `Bearer undefined` e il
    // server le respingerebbe una per una.
    if (!nuovo) throw new Error('Rinnovo della sessione senza access token')
    impostaAccess(nuovo)
    return nuovo
  })).finally(() => {
    rinnovoInVolo = null
  })
  return rinnovoInVolo
}
