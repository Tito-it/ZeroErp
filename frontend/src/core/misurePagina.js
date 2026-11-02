// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ LE MISURE «RIGHE PER PAGINA» — quali il paginatore offre e quali
//        sono i default — lette dal DATABASE, la sede unica
//        (`ui.misure_pagina`, brief-db-misure-pagina-catalogo, decisioni di
//        Tid del 2026-09-29). Fino al 2026-09-30 erano la costante
//        `PAGINATION` di `constants.js`, una terza copia accanto al resolver
//        delle liste e al preset: un preset a 15 lasciava il selettore vuoto
//        senza nessun errore.
//
// ⭐ UN USO, NON UN NUMERO. Chi pagina dichiara PER COSA pagina:
//    `USO_MISURA.COMPATTA` (drawer e dialog, dove l'altezza e' quella di
//    poche righe) o `USO_MISURA.PAGINA` (una pagina intera). Il numero lo dice
//    il catalogo. Spostare un default e' una riga del CSV, non un giro sul FE.
//
// ⭐ QUANDO SI CARICANO. Una volta per sessione, dal guard del router
//    (`caricaMisurePagina`, atteso), prima di aprire qualunque pagina del
//    namespace operatore (decisione di Tid del 2026-09-30). Per questo le
//    letture qui sotto sono SINCRONE: quando una lista nasce, le misure ci
//    sono gia'.
//
// ⛔ NESSUN RIPIEGO SCRITTO QUI. Se la chiamata fallisce la navigazione si
//    ferma; un «10/25 finche' non arriva» sarebbe una quarta copia del
//    catalogo, che diverge al primo cambio del CSV.
// ⛔ E NIENTE LETTURA ALL'IMPORT. Uno store che scrive il NUMERO nelle sue
//    opzioni a livello di modulo lo leggerebbe prima del guard: le opzioni
//    portano l'USO (`misura: USO_MISURA.COMPATTA`), e il numero si risolve
//    quando lo store nasce. Una lettura prima del caricamento non ripiega:
//    solleva, perche' e' un errore di programmazione.
// ------------------------------------------------------------

import { BREAKPOINTS } from './constants'

// Gli usi dichiarati dal catalogo (`ui.misure_pagina.uso_default`).
export const USO_MISURA = Object.freeze({
  COMPATTA: 'COMPATTA',
  PAGINA: 'PAGINA',
})

// `null` = non ancora caricate. Non e' stato dell'utente: il catalogo e' lo
// stesso per tutti, quindi non si azzera al logout.
let misure = null
let inVolo = null

// Scopo: registra la risposta di `GET /ui/misure-pagina/`, controllandone la
//        forma. Esposta anche per i test, che le misure le fabbricano.
export function registraMisurePagina(dati) {
  const opzioni = dati?.misure
  // ⚠️ Strettamente crescenti: e' l'ordine del selettore, e il DB lo promette.
  //    Una risposta in un altro ordine si RIFIUTA, non si riordina in silenzio.
  const ok = Array.isArray(opzioni) && opzioni.length > 0
    && opzioni.every((m, i) => Number.isInteger(m) && m > 0 && (i === 0 || m > opzioni[i - 1]))
    && opzioni.includes(dati.default_compatta)
    && opzioni.includes(dati.default_pagina)
  if (!ok) {
    throw new Error(`misure di pagina: risposta non valida (${JSON.stringify(dati)})`)
  }
  misure = Object.freeze({
    opzioni: Object.freeze([...opzioni]),
    [USO_MISURA.COMPATTA]: dati.default_compatta,
    [USO_MISURA.PAGINA]: dati.default_pagina,
  })
}

// Scopo: carica le misure, una volta. Chiamate concorrenti condividono la
//        stessa richiesta; un fallimento non resta in memoria (la prossima
//        navigazione riprova).
export async function caricaMisurePagina() {
  if (misure) return
  // ⚠️ Import DINAMICO del client: statico, trascinerebbe axios e i18n in
  //    chiunque legga una misura (store, composable) — e nei test in node.
  inVolo ??= import('./api/ui-api')
    .then(({ getMisurePagina }) => getMisurePagina())
    .then((res) => registraMisurePagina(res.data?.data))
    .finally(() => { inVolo = null })
  await inVolo
}

function leggi() {
  if (!misure) {
    throw new Error(
      'misure di pagina lette prima del caricamento: si caricano nel guard '
      + 'del router, e uno store dichiara l\'USO (`misura`), non il numero',
    )
  }
  return misure
}

// Scopo: le misure che ogni paginatore offre, in ordine crescente.
export function misureOpzioni() {
  return leggi().opzioni
}

// Scopo: la misura di partenza per un uso (default: una pagina intera).
export function misuraDefault(uso = USO_MISURA.PAGINA) {
  const valore = leggi()[uso]
  if (valore === undefined) throw new Error(`misure di pagina: uso sconosciuto «${uso}»`)
  return valore
}

// Scopo: la misura di partenza di una lista STANDARD secondo lo schermo — la
//        compatta sotto il tablet, quella di pagina sopra. Una sede sola:
//        fino al 2026-09-30 la stessa regola era scritta due volte
//        (`usePagination`, `useSearchTable`).
//        `width <` e non `max-width: TABLET - 1`: con lo zoom la larghezza e'
//        frazionaria, e fra 1023 e 1024 il CSS e questa soglia non
//        concorderebbero.
//        La media query e' esposta per chi deve anche ASCOLTARNE il cambio
//        (`useSearchTable`): la soglia resta scritta qui.
export const QUERY_VIEWPORT_COMPATTO = `(width < ${BREAKPOINTS.TABLET}px)`

export function misuraPerViewport() {
  const compatto = typeof window !== 'undefined'
    && window.matchMedia(QUERY_VIEWPORT_COMPATTO).matches
  return misuraDefault(compatto ? USO_MISURA.COMPATTA : USO_MISURA.PAGINA)
}
