// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La licenza del programma e gli indirizzi che l'interfaccia offre a
//        chi la usa (AGPL-3.0 §13: chi usa il programma in rete deve poterne
//        ricevere il sorgente): il codice sorgente e il testo della licenza.
//        Li legge il dialog «Informazioni» (`InformazioniDialog`), che si
//        apre dalle pagine di accesso (`LinkInformazioni`) e dal kebab utente
//        (`AppTopbar`).
// Note: ⭐ Decisione di Tid, 2026-11-02. Gli indirizzi sono variabili di
//       BUILD (`VITE_SOURCE_URL`, `VITE_LICENSE_URL`), non parametri del DB:
//       l'offerta deve esserci anche sulla pagina di login, prima di
//       qualunque chiamata autenticata, e chi rimette in rete una versione
//       modificata li punta al PROPRIO sorgente senza toccare il codice.
//       Senza variabili vale il repository ufficiale.
// ------------------------------------------------------------

export const CODICE_SORGENTE_URL_PREDEFINITO = 'https://github.com/Tito-it/ZeroErp'

// La licenza come identificatore SPDX: la stessa riga in testa a ogni file.
export const LICENZA_SPDX = 'AGPL-3.0-or-later'
export const COPYRIGHT = 'Copyright (C) 2026 Tid (Michele Carlo Titini)'

// Scopo: il valore, ripulito, se e' un indirizzo http(s) che porta da qualche
//        parte; altrimenti `null`.
// ⚠️ Lo decide il parser `URL`, non un prefisso: `https://` da solo o
//    `https://host con spazi` passerebbero un test sul prefisso e non
//    porterebbero da nessuna parte — il difetto che nessuno vede. Un `href`
//    vuoto riaprirebbe la pagina stessa, e uno `javascript:` non e' un link.
function urlHttp(valore) {
  const url = typeof valore === 'string' ? valore.trim() : ''
  let analizzato
  try {
    analizzato = new URL(url)
  } catch {
    return null
  }
  const { protocol, hostname } = analizzato
  return (protocol === 'https:' || protocol === 'http:') && hostname && !/\s/.test(url) ? url : null
}

// Scopo: l'indirizzo del sorgente, dato il valore della variabile di build.
//        Non valido → il repository ufficiale.
export function risolviUrlCodiceSorgente(valore) {
  return urlHttp(valore) ?? CODICE_SORGENTE_URL_PREDEFINITO
}

// Scopo: l'indirizzo del testo della licenza. Senza variabile (o non valida)
//        e' il file `LICENSE` del sorgente: e' il testo che accompagna QUELLA
//        versione, e chi punta il sorgente al proprio fork si porta dietro
//        anche la licenza giusta.
// ⚠️ `blob/HEAD/`, non `blob/main/`: il ramo predefinito lo risolve l'host
//    (GitHub e GitLab), e non si cabla il nome di un ramo. Un host con un
//    altro schema di indirizzi passa `VITE_LICENSE_URL`.
export function risolviUrlLicenza(valore, urlSorgente) {
  const base = urlSorgente.replace(/\/+$/, '').replace(/\.git$/, '')
  return urlHttp(valore) ?? `${base}/blob/HEAD/LICENSE`
}

// ⚠️ `import.meta.env?.`: questo modulo lo carica anche node (vitest lo
//    valorizza, uno script puro no), e senza Vite `import.meta.env` non esiste.
export const CODICE_SORGENTE_URL = risolviUrlCodiceSorgente(import.meta.env?.VITE_SOURCE_URL)
export const LICENZA_URL = risolviUrlLicenza(import.meta.env?.VITE_LICENSE_URL, CODICE_SORGENTE_URL)
