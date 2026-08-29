// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La conversione `limit`/`offset` -> `page`/`page_size` delle liste
//        paginate PAGE-BASED, in un punto solo.
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
  const p = {
    page: Math.floor((f.offset || 0) / pageSize) + 1,
    page_size: pageSize,
  }
  if (f.order_by) {
    p.order_by = f.order_by
    p.order_dir = f.order_dir || orderDirDefault
  }
  return p
}
