// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: registro delle ATTIVITA' UI lanciabili da un flusso di pratica.
//        Specchio frontend di pratiche.handler_flussi/HANDLER_MAP (automazione
//        server), qui per le attivita' INTERATTIVE: una chiave `azione_ui_key`
//        (catalogo DB pratiche.azioni_ui, esposta sul flusso come
//        `template_azione_ui_key`) risolve al drawer di dominio da aprire dal
//        flusso, ai campi che eredita/blocca dal contesto pratica e al gancio
//        post-salvataggio.
//
// ⭐ Il motore delle pratiche NON conosce i domini (decisione Tid, 2026-09-26,
//    frontend-standards §«Confini fra domini»): possiede il registro, e ogni
//    dominio iscrive le proprie voci dal suo `iscrizioni.js`. Aggiungere un
//    documento = iscriverlo dal suo dominio + seedare la chiave sul template
//    DB. Nessun `if` per tipo_prestazione: l'asimmetria fra documenti vive
//    nei DATI della voce.
//
// Forma della voce:
//   loadComponent()          → import dinamico del drawer (l'host attende la
//                              risoluzione PRIMA di montarlo, cosi' il suo
//                              watch(visible) vede false→true);
//   resolveExisting(ctx)     → id del documento gia' agganciato, o null;
//   buildProps(ctx, id)      → props del drawer;
//   savedId(result)?         → id dall'evento `saved`;
//   onSaved(id, ctx)?        → aggancio post-salvataggio (response axios);
//   requiresActiveClient,
//   requiresExisting?        → gating dell'apertura;
//   label, icon, linkedMessage? → testi i18n e icona.
// ------------------------------------------------------------
import { creaRegistro } from '../core/registri'

const registro = creaRegistro('attivita-ui-flusso')

// Scopo: iscrive l'attivita' di una chiave `azione_ui_key`.
export function iscriviAttivitaUi(chiave, voce) {
  registro.iscrivi(chiave, voce)
}

// Scopo: la voce di una chiave `azione_ui_key`; null se assente o non
//        iscritta (fail-safe: nessun pulsante invece di un errore).
export function getUiActivity(key) {
  return registro.voce(key)
}
