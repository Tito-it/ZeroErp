// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ L'ASPETTO DI UN VERBO DI STATO — icona e colore — in una sede sola.
//        Le `script.fn_available_actions_*` mandano il verbo (`key`), non come
//        si disegna: il verbo E' gia' il significato, e la presentazione esce
//        dal DB (brief-db-icone-azioni-per-significato: D-1 per l'icona,
//        §6.4 riaperta per il colore, Tid 2026-09-27). Qui il verbo diventa
//        la sua costante di icona e la sua severity.
//
// ⛔ UN ASPETTO PER VERBO, in tutti i domini: `emetti` e' lo stesso pulsante
//    nel DDT e nel preventivo. Se un giorno un verbo volesse aspetti diversi
//    per dominio, la chiave diventa `(dominio, verbo)` — non si aggiunge un
//    `if`.
// ⚠️ Resta al DB cio' che NON dipende dal verbo: `label_key` (cambia per
//    documento) e `outlined` (cambia per stato: l'annulla di una bozza e'
//    solo bordato).
//
// ⚠️ Un verbo nuovo a DB senza voce qui prende `RIPIEGO`: si vede (una freccia
//    di cambio stato, colore neutro), non sparisce. `aspettoAzioni.spec.js`
//    fissa l'elenco.
//
// Lettori: `mapAvailableActionsToDrawerActions` (barra dei drawer),
//          `useLottoAzioni` (kebab della lista lotti), le conferme che
//          ripetono il pulsante (DocumentoInternoDrawer).
// ------------------------------------------------------------
import { MANAGE_ICONS } from './constants'

export const ASPETTO_AZIONE = Object.freeze({
  // Comuni a piu' matrici
  annulla: { icona: MANAGE_ICONS.ANNULLA, severity: 'danger' },
  // Tid 2026-09-27: `info` (i resi e il documento interno avevano `success`).
  conferma: { icona: MANAGE_ICONS.CONFIRM, severity: 'info' },
  // Il «si'» e il «no» del cliente (preventivi, offerte).
  accetta: { icona: MANAGE_ICONS.APPROVE, severity: 'success' },
  rifiuta: { icona: MANAGE_ICONS.REJECT, severity: 'danger' },
  // D-1 di Tid: `pi-send` ovunque, DDT compreso.
  emetti: { icona: MANAGE_ICONS.SEND, severity: 'info' },
  // DDT
  spedisci: { icona: MANAGE_ICONS.SPEDISCI, severity: 'info' },
  consegna: { icona: MANAGE_ICONS.CONSEGNA, severity: 'success' },
  // Il reso apre un documento nuovo che rovescia il DDT.
  reso: { icona: MANAGE_ICONS.CORREZIONE, severity: 'warn' },
  // Contratti: `cessa` chiede la data di cessazione (stato terminale con data).
  attiva: { icona: MANAGE_ICONS.PLAY, severity: 'info' },
  cessa: { icona: MANAGE_ICONS.CLOSE_DATE, severity: 'danger' },
  // Commessa
  rendi_pronta: { icona: MANAGE_ICONS.RENDI_PRONTA, severity: 'success' },
  chiudi: { icona: MANAGE_ICONS.CLOSE, severity: 'success' },
  // D-1 di Tid: `riapri` e `riporta_a_draft` sono lo stesso gesto, e tornare
  // indietro e' un gesto di cautela: `warn` (Tid 2026-09-27; la commessa
  // aveva `info`, il documento interno `secondary`).
  riapri: { icona: MANAGE_ICONS.RIPORTA_A_BOZZA, severity: 'warn' },
  riporta_a_draft: { icona: MANAGE_ICONS.RIPORTA_A_BOZZA, severity: 'warn' },
  // Lotto
  numera: { icona: MANAGE_ICONS.NUMERA, severity: 'success' },
  ristampa: { icona: MANAGE_ICONS.STAMPA, severity: 'secondary' },
  // Verbi scritti nelle funzioni, fuori dalle matrici
  crea_revisione: { icona: MANAGE_ICONS.NUOVA_REVISIONE, severity: 'info' },
  // Tid 2026-09-27: non `SEND`, che e' `emetti` nello stesso drawer; e
  // `success` ovunque (il preventivo aveva `info`), come il pulsante negato
  // (`AZIONE_PUSH_COMMESSA`).
  push_commessa: { icona: MANAGE_ICONS.INVIA_A_COMMESSA, severity: 'success' },
  // Un documento che nasce da un altro.
  push_contratto: { icona: MANAGE_ICONS.GENERA_DOCUMENTO, severity: 'success' },
  genera_ordine: { icona: MANAGE_ICONS.GENERA_DOCUMENTO, severity: 'info' },
})

// L'aspetto di un verbo che la mappa non conosce: dice «cambia stato», con un
// colore neutro.
export const RIPIEGO = Object.freeze({ icona: MANAGE_ICONS.CAMBIO_STATO, severity: 'secondary' })

export function aspettoAzione(key) {
  return Object.hasOwn(ASPETTO_AZIONE, key ?? '') ? ASPETTO_AZIONE[key] : RIPIEGO
}
