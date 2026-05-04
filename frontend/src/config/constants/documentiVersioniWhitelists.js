// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Whitelist FE allineate ai CHECK del DDL Tranche F (versioni
//        template) e Tranche G (asset). Il backend e' la fonte di
//        verita': se questi set divergono dai CHECK DDL il save fallisce
//        con messaggio parlante (mapping integrity error). Documentate
//        qui per coerenza UX (dropdown popolati senza round-trip BE).
// ------------------------------------------------------------

// Set chiusi DDL `template_documenti_versioni`:
//  - chk_template_documenti_versioni_page_format
//  - chk_template_documenti_versioni_page_orientation
//  - chk_template_documenti_versioni_formato_template
export const PAGE_FORMATS = ['A4', 'A5', 'LETTER']
export const PAGE_ORIENTATIONS = ['PORTRAIT', 'LANDSCAPE']
export const FORMATI_TEMPLATE = ['HTML', 'MARKDOWN']

// Limite size upload asset documentale (Tranche G `_MAX_FILE_BYTES`
// service-side). v1: 25 MB hardcoded sia FE sia BE. Il vero limite e'
// applicato dal BE via parameter `documenti_asset_upload_max_mb`
// (default 25); questo costante FE serve solo come guard early-return
// per evitare upload destinati a fallire.
export const ASSET_UPLOAD_MAX_MB = 25
export const ASSET_UPLOAD_MAX_BYTES = ASSET_UPLOAD_MAX_MB * 1024 * 1024
