// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La finestra `limit`/`offset` delle liste, in un punto solo
//        (`paramsFinestra`; fino al 2026-10-21 la conversione verso
//        `page`/`page_size`, ritirata col dialetto) — e, dal 2026-09-18,
//        l'ORDINAMENTO come lo chiede il backend (`paramsOrdinamento`), che
//        serve sia alla fetch della lista sia al suo export.
// Note: ⚠️ Perche' esiste. `useSearchTable` governa `limit`/`offset` — e' la
//       lingua del building block, della DataTable e (dal 2026-10-21) di ogni
//       lista del backend. Fino a quel giorno una parte degli endpoint
//       paginava con `page`/`page_size`, e la stessa aritmetica di traduzione
//       era scritta a mano in tre domini.
//       ⭐ Estratto il 2026-08-28 con la regola del 2 (ok di Tid) alla TERZA
//       sede: `vendite/stores/lotti`, `vendite/stores/fondiFatturaDaDecidere` e
//       le quattro liste di `pagamenti`.
//       ⭐ Dal 2026-09-24 anche la RICERCA LIBERA (`paramsRicerca`,
//       `termineCorto`): la soglia del termine era scritta in sei store e due
//       volte nel BB di stato della lista.
//       ⭐ Dal 2026-09-26 la soglia e' della LISTA: arriva dalla configurazione
//       (`ricerca_min_caratteri`, brief-db-be-fe-ricerca-soglia-per-lista), il
//       BB di stato la tiene (`ricercaMinCaratteri`) e la passa qui come
//       `minCaratteri`. Nessun numero nuovo nel codice: `RICERCA.MIN_CARATTERI`
//       resta il ripiego finche' la configurazione non e' arrivata.
// ------------------------------------------------------------

import { RICERCA } from '../constants'
import { USO_MISURA, misuraDefault } from '../misurePagina'

// Scopo: la finestra della lista come la chiede il backend — `limit`/`offset`,
//        piu' l'ordinamento quando c'e'. Cio' che varia — i filtri di dominio —
//        resta al chiamante, che e' l'unico a sapere come si chiamano.
//
// ⭐ Un dialetto solo (2026-10-21, decisione Tid): fino a quel giorno una
//    ventina di liste del backend paginava con `page`/`page_size`, e questa
//    funzione si chiamava `paramsPagina` e traduceva `limit`/`offset` nella
//    loro lingua. Ora il backend le rifiuta con un 400 (`pagina_da_query`):
//    la traduzione non serve piu', e la funzione resta il punto in cui la
//    finestra prende la sua forma.
//
// @param {object} f - i filtri dello store (`limit`, `offset`, `order_by`, `order_dir`).
// @param {object} [opts]
// @param {number} [opts.limitDefault] - finestra di ripiego (default: la misura di pagina).
// @param {'asc'|'desc'} [opts.orderDirDefault='desc'] - verso di ripiego quando
//        `order_by` c'e' e `order_dir` no.
// @returns {{limit:number, offset:number, order_by?:string, order_dir?:string}}
//
// ⚠️ IL GUARD SUL LIMIT (`> 0`) NON E' PRUDENZA: il backend riporta uno `0`
//    o un negativo a 1 riga, e una lista di una riga sembra una lista vuota
//    sbagliata invece di una finestra sbagliata.
//
// ⛔ `orderDirDefault` E' UN PARAMETRO, e la ragione va letta prima di
//    toglierlo: le copie da cui e' nata NON erano identiche — `lotti` ripiegava
//    su `asc`, le altre su `desc`. Oggi il ripiego non scatta (tutte tengono
//    `order_dir` sempre valorizzato nei filtri), ma unificarlo avrebbe
//    cambiato il verso di una lista il giorno in cui quel ramo si fosse
//    acceso. Un'estrazione appiana la duplicazione, non le differenze.
export function paramsFinestra(f, {
  limitDefault = misuraDefault(USO_MISURA.PAGINA),
  orderDirDefault = 'desc',
} = {}) {
  return {
    limit: f.limit > 0 ? f.limit : limitDefault,
    offset: f.offset > 0 ? f.offset : 0,
    ...paramsOrdinamento(f, { orderDirDefault }),
  }
}

// Scopo: l'ordinamento della lista come lo chiede il backend — `order_by` e
//        `order_dir` quando un ordinamento c'e', NIENTE altrimenti (mandarlo
//        vuoto significherebbe chiedere al backend un ordinamento che poi lui
//        scarta: la cosa giusta per il motivo sbagliato).
//
// ⭐ Estratto il 2026-09-18 (regola del 2, ok Tid) alla DODICESIMA copia del
//    blocco «l'export segue l'ordinamento a video» nei `getExportParams`
//    (`if (store.filters.order_by) { p.order_by = …; p.order_dir = … || X }`):
//    lo stesso blocco viveva anche dentro `paramsPagina` (oggi `paramsFinestra`) qui sopra e nel
//    `buildParams` di `useListaStoreCore`, che ora chiamano questa funzione.
//    Il file che scarichi e' la lista che stai guardando, e la forma con cui la
//    lista chiede l'ordine al backend e' UNA.
//
// ⛔ `orderDirDefault` resta un parametro, per la stessa ragione scritta su
//    `paramsFinestra`: le copie NON erano identiche (`asc` sugli store di
//    `useListaStoreCore`, `desc` sui documenti di vendita). Oggi il ripiego non
//    scatta — `useSearchTable.onSort` scrive sempre `order_by` e `order_dir`
//    insieme — ma appianarlo avrebbe cambiato il verso di una lista il giorno
//    in cui quel ramo si accendesse. Un'estrazione appiana la duplicazione,
//    non le differenze. ⚠️ Chi scrive l'export di una lista passa lo STESSO
//    ripiego della fetch di quella lista: e' l'unico modo perche' il file segua
//    davvero la videata anche in quel ramo (trovato divergente sui lotti, 18/09).
//
// @param {object} f - i filtri dello store (`order_by`, `order_dir`).
// @param {object} [opts]
// @param {'asc'|'desc'} [opts.orderDirDefault='desc'] - verso di ripiego quando
//        `order_by` c'e' e `order_dir` no.
// @returns {{order_by?:string, order_dir?:string}}
export function paramsOrdinamento(f, { orderDirDefault = 'desc' } = {}) {
  if (!f?.order_by) return {}
  return { order_by: f.order_by, order_dir: f.order_dir || orderDirDefault }
}

// Scopo: il termine di ricerca dei filtri, ripulito dagli spazi — la forma in
//        cui il backend lo riceve (il BB del backend fa lo stesso `strip`).
// @param {object} f - i filtri dello store (`search`).
// @returns {string}
export function termineRicerca(f) {
  return (f?.search || '').trim()
}

// Scopo: un termine c'e' ma e' ancora troppo corto per cercare («sto
//        digitando»). E' la domanda del BB di stato della lista
//        (`useListaEmptyStateFetch`, guardia empty-state e opzione
//        `ricercaCorta` — che e' un'altra cosa: cosa FARE col termine corto).
// ⚠️ Termine vuoto → `false`: «nessuna ricerca» e «ricerca corta» sono due
//    stati diversi, e la guardia empty-state li tratta in due modi.
// @param {string} termine - gia' trimmato (`termineRicerca`).
// @param {object} [opts]
// @param {number|null} [opts.minCaratteri] - la soglia della lista
//        (`ricercaMinCaratteri` dello store); `null`/assente = non ancora nota,
//        vale `RICERCA.MIN_CARATTERI`.
// @returns {boolean}
// ⚠️ `??` e non un default di parametro: il default scatta solo su
//    `undefined`, e lo store tiene `null` finche' la configurazione non arriva
//    — un `termine.length < null` direbbe «mai corto» e manderebbe ogni lettera.
export function termineCorto(termine, { minCaratteri } = {}) {
  return termine.length > 0 && termine.length < (minCaratteri ?? RICERCA.MIN_CARATTERI)
}

// Scopo: il parametro `search` come lo chiede il backend — il termine trimmato
//        da `minCaratteri` in su, NIENTE sotto (la lista resta quella di prima
//        mentre si digita).
// ⭐ Estratto il 2026-09-24 (regola del 2, ok Tid): la stessa riga
//    `trim` + `>= 3` viveva in `useListaStoreCore.paramsFiltro`, `resiCoda` e
//    nei quattro store di pagamenti scritti a mano. Fetch ed export la
//    chiedono qui, cosi' il file scaricato cerca come la videata.
// @param {object} f - i filtri dello store (`search`).
// @param {object} [opts]
// @param {number|null} [opts.minCaratteri] - la soglia della lista (vedi
//        `termineCorto`).
// @returns {{search?: string}}
export function paramsRicerca(f, { minCaratteri } = {}) {
  const termine = termineRicerca(f)
  return termine && !termineCorto(termine, { minCaratteri }) ? { search: termine } : {}
}
