// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Whitelist FE allineate ai CHECK del DDL Tranche F (versioni
//        template). Il backend e' la fonte di verita': se questi set
//        divergono dai CHECK DDL il save fallisce con messaggio parlante.
// ⏳ DEBITO DICHIARATO (2026-10-03): sono una COPIA dei CHECK, e il giorno
//    in cui e' stato scritto questo avviso la copia era GIA' divergente
//    (offriva `MARKDOWN` e `A5`, che il DB rifiuta, e non `HTML_MARKDOWN_
//    BLOCKS` ne' `A3`): riallineata al corpo vero dei CHECK. Per leggerli
//    serve un vocabolario a DB (brief-db-vocabolari-versione-template.md);
//    allora questo file si ritira.
// ------------------------------------------------------------

// Set chiusi DDL `template_documenti_versioni`:
//  - chk_template_documenti_versioni_page_format
//  - chk_template_documenti_versioni_page_orientation
//  - chk_template_documenti_versioni_formato_template
export const PAGE_FORMATS = ['A4', 'A3', 'LETTER']
export const PAGE_ORIENTATIONS = ['PORTRAIT', 'LANDSCAPE']
export const FORMATI_TEMPLATE = ['HTML', 'HTML_MARKDOWN_BLOCKS']
