// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL CODICE DELL'AZIONE DI RIGA «togli dal giro» nel registro del DB
//        (`config.azioni_riga`), sede unica lato frontend.
// ------------------------------------------------------------
//
// ⭐ Dal 2026-10-27 (brief-modello-documento-vendita §15.11.2, FE-1) il motivo
//    del pulsante spento lo legge il BB `useAzioneRiga`, che dal registro sa
//    QUALI colonne della riga guardare. Qui restava `motivoUscitaBloccata`, che
//    le colonne le scriveva a mano (`uscita_blocco_reason`, `…_key`): ritirata.
//    Le tre superfici del verbo (la casella della scheda Documenti, l'azione di
//    riga della stessa scheda, quella della scheda Critiche) passano tutte dal
//    BB con questo codice, e dicono la stessa frase per costruzione.
export const AZIONE_RIGA_USCITA_DAL_GIRO = 'ESCLUDI_DOCUMENTO_DA_GIRO'
