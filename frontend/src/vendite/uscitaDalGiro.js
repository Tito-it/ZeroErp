// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL MOTIVO PER CUI UN DOCUMENTO NON SI PUÒ TOGLIERE DAL GIRO, letto da
//        una riga — sede unica del §12.5 per il verbo «togli dal giro».
// ------------------------------------------------------------
//
// ⛔ NON RICALCOLA NIENTE, ed è l'unica cosa che questo file deve garantire: il
//    verdetto arriva in riga da `script.fn_check_documento_escludibile_da_giro`,
//    cioè la STESSA funzione con cui il database RIFIUTA. Qui si traduce, non si
//    decide — un predicato riscritto farebbe dire due cose diverse al tooltip e
//    all'errore, che è precisamente il difetto che il §12.5 esiste per togliere.
//
// ⭐ ESTRATTO 2026-09-08 (regola del 2, e le occorrenze erano TRE): la casella
//    di selezione della scheda Documenti, l'azione di riga della stessa scheda e
//    l'azione di riga della scheda Critiche leggevano le stesse due colonne con
//    la stessa `labelOrCode`. Tre copie della stessa lettura sono tre posti in
//    cui il giorno che il contratto aggiunge una colonna — o cambia il verso di
//    `null` — due si aggiornano e una no, **senza fallire**: il pulsante resta
//    vivo, il database rifiuta, e l'operatore legge un errore dove si aspettava
//    un tooltip.
//
// ⚠️ `labelOrCode` e non `t()` secco: una `reason_key` che i locales non
//    conoscono ancora mostra il CODICE grezzo invece del vuoto — fail-visible.
//    Il vocabolario dei motivi vive a database ed è estensibile: il frontend
//    arriva sempre dopo.
import { labelOrCode } from '../core/utils/i18nLabel'

// Scopo: il motivo per cui l'uscita è bloccata su QUESTA riga, già tradotto.
// ⚠️ `undefined` quando l'azione è AMMESSA, e non stringa vuota: è il valore che
//    `RowActionsMenu` e la casella leggono come «nessun motivo da mostrare». Una
//    stringa vuota farebbe comparire un tooltip senza testo, cioè un rettangolo.
// ⚠️ Il `null` del backend NON vuol dire «si può fare» su una riga che non
//    nomina nessun documento: là il verbo non ha oggetto e la domanda non è
//    stata posta. Chi rende distingue i due casi dalla `gruppo_key`, che è
//    l'unica cosa che li separa.
export function motivoUscitaBloccata(t, te, row) {
  if (!row?.uscita_blocco_reason) return undefined
  return labelOrCode(t, te, row.uscita_blocco_reason_key, row.uscita_blocco_reason)
}
