// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La conversione `limit`/`offset` -> `page`/`page_size` delle liste
//        paginate PAGE-BASED, in un punto solo — e, dal 2026-09-18,
//        l'ORDINAMENTO come lo chiede il backend (`paramsOrdinamento`), che
//        serve sia alla fetch della lista sia al suo export.
// Note: ⚠️ Perche' esiste. `useSearchTable` governa `limit`/`offset` — e' la
//       lingua del building block e della DataTable; una parte degli endpoint
//       pagina invece con `page`/`page_size`. La traduzione fra le due lingue
//       sta nel `buildParams` dello store, che e' il confine giusto: ne'
//       l'endpoint ne' il BB si adattano all'altro. Ma la stessa aritmetica era
//       scritta a mano in tre domini, e alla prima correzione sarebbe
//       divergente.
//       ⭐ Estratto il 2026-08-28 con la regola del 2 (ok di Tid) alla TERZA
//       sede: `vendite/stores/lotti`, `vendite/stores/fondiFatturaDaDecidere` e
//       le quattro liste di `pagamenti`.
// ------------------------------------------------------------

import { PAGINATION } from '../constants'

// Scopo: i due parametri di pagina che un endpoint page-based si aspetta, piu'
//        l'ordinamento quando c'e'. Cio' che varia — i filtri di dominio —
//        resta al chiamante, che e' l'unico a sapere come si chiamano.
//
// @param {object} f - i filtri dello store (`limit`, `offset`, `order_by`, `order_dir`).
// @param {object} [opts]
// @param {number} [opts.pageSizeDefault] - pagina di ripiego (default: il 25 di progetto).
// @param {'asc'|'desc'} [opts.orderDirDefault='desc'] - verso di ripiego quando
//        `order_by` c'e' e `order_dir` no.
// @returns {{page:number, page_size:number, order_by?:string, order_dir?:string}}
//
// ⚠️ IL GUARD SUL LIMIT NON E' PRUDENZA. Uno `0` produrrebbe una divisione per
//    zero e una `page` **NaN**, che il backend rifiuta con un 400 illeggibile —
//    un errore che sembra un difetto del server invece che una pagina sbagliata.
//    ⭐ E il confronto e' `> 0`, non il `||` che una delle tre copie usava: con
//    `||` un `limit` NEGATIVO passa intero e produce una `page` negativa. Il
//    caso oggi non capita da nessuna parte, e infatti non e' per questo che si
//    stringe: si stringe perche' il ramo esiste.
//
// ⛔ `orderDirDefault` E' UN PARAMETRO, e la ragione va letta prima di
//    toglierlo: le tre copie NON erano identiche — `lotti` ripiegava su `asc`,
//    le altre due su `desc`. Oggi il ripiego non scatta in nessuna delle tre
//    (tutte tengono `order_dir` sempre valorizzato nei filtri), quindi
//    unificarlo sarebbe stato invisibile **e** avrebbe cambiato il verso di una
//    lista che si apre col piu' recente in cima, il giorno in cui quel ramo si
//    fosse acceso. Un'estrazione appiana la duplicazione, non le differenze.
export function paramsPagina(f, {
  pageSizeDefault = PAGINATION.DEFAULT_ROWS,
  orderDirDefault = 'desc',
} = {}) {
  const pageSize = f.limit > 0 ? f.limit : pageSizeDefault
  return {
    page: Math.floor((f.offset || 0) / pageSize) + 1,
    page_size: pageSize,
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
//    lo stesso blocco viveva anche dentro `paramsPagina` qui sopra e nel
//    `buildParams` di `useListaStoreCore`, che ora chiamano questa funzione.
//    Il file che scarichi e' la lista che stai guardando, e la forma con cui la
//    lista chiede l'ordine al backend e' UNA.
//
// ⛔ `orderDirDefault` resta un parametro, per la stessa ragione scritta su
//    `paramsPagina`: le copie NON erano identiche (`asc` sugli store di
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
