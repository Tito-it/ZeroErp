// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: registro degli step il cui COMPLETAMENTO e' guidato dal DOMINIO —
//        l'esito e' CALCOLATO dal backend (bivio), non scelto dall'operatore.
//        Per questi step il FlussoDrawer SOPPRIME il picker esito e offre una
//        sola azione che chiama l'endpoint di dominio: il BE calcola l'esito di
//        RAMO, verifica gli invarianti e completa lo step nella stessa
//        transazione.
//
// Differenza da flussoCompletionRegistry: la', l'esito resta un verdetto
// scelto dall'operatore e la dialog raccoglie solo dati di processo (meta).
// Qui l'esito stesso e' un bivio calcolato (es. SMISTAMENTO →
// MERCE_PRESENTE/SOLO_SERVIZI, che decide se attivare i flussi merce).
//
// ⭐ FlussoDrawer resta GENERICO e il motore non conosce i domini: ogni
//    dominio iscrive le proprie voci dal suo `iscrizioni.js` (decisione Tid,
//    2026-09-26).
//
// Forma della voce:
//   label:    chiave i18n del bottone di completamento;
//   complete: async ({ praticaId, flusso }) => Promise<AxiosResponse> — l'host
//             la avvolge in useApiHandler.execute, quindi DEVE risolvere in una
//             response axios; un throw e' gestito da execute come errore.
// ------------------------------------------------------------
import { creaRegistro } from '../core/registri'

const registro = creaRegistro('completamento-dominio-flusso')

// Scopo: iscrive il completamento di dominio di un `template_flusso_codice`.
export function iscriviCompletamentoDominio(codice, voce) {
  registro.iscrivi(codice, voce)
}

// Scopo: la voce di un `template_flusso_codice`; null se assente (fail-safe:
//        lo step usa il completamento generico con picker esito).
export function getDomainCompletion(codice) {
  return registro.voce(codice)
}
