// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: registro delle DIALOG DI COMPLETAMENTO di un flusso di pratica.
//        Gemello di uiActivityRegistry, ma per il momento «completa flusso»:
//        alcuni step richiedono dati di processo all'esito (es.
//        APPROVAZIONE_CLIENTE su POSITIVO chiede modalita'+competenza di
//        fatturazione, che l'accettazione del preventivo persiste). La chiave
//        e' il `template_flusso_codice` esposto sul flusso.
//
// ⭐ FlussoDrawer resta GENERICO e il motore non conosce i domini: ogni
//    dominio iscrive le proprie voci dal suo `iscrizioni.js` (decisione Tid,
//    2026-09-26). Il dialog deve accettare v-model:visible ed emettere
//    `confirm` con un payload gia' BE-ready, che l'host inoltra come `meta`.
//
// Forma della voce: `esitoRichiesto`, `loadComponent()`, e per gli step
// guidati dal documento `esitoToStato` + `docAction({ praticaId, esito, meta })`.
// ------------------------------------------------------------
import { creaRegistro } from '../core/registri'

const registro = creaRegistro('dialog-completamento-flusso')

// Scopo: iscrive la dialog di completamento di un `template_flusso_codice`.
export function iscriviDialogCompletamento(codice, voce) {
  registro.iscrivi(codice, voce)
}

// Scopo: la voce di un `template_flusso_codice`; null se assente (fail-safe:
//        completamento generico senza dialog).
export function getCompletionDialog(codice) {
  return registro.voce(codice)
}
