// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Whitelist hardcoded codici `context_builder_code` ammessi
//        nel form testata template documentale (Tranche L). La
//        whitelist effettiva e' lato BE in
//        `apps.documenti.services.context_builders.registry` —
//        questa lista FE deve restare sincronizzata: aggiungere un
//        builder concreto (es. CONTRATTO) richiede:
//         1) registro BE via VenditeConfig.ready() / dominio sorgente;
//         2) entry qui;
//         3) chiave i18n `documenti.context_builders.<CODE>`.
//
//        PREVENTIVO, CONTRATTO, OFFERTA_COMMERCIALE e ORDINE_VENDITA sono
//        registrati lato BE (VenditeConfig.ready()). Aggiungere un builder
//        concreto richiede: registro BE + entry qui + chiave i18n.
// ------------------------------------------------------------

export const CONTEXT_BUILDER_CODES = [
  { code: 'PREVENTIVO',         i18nKey: 'documenti.context_builders.PREVENTIVO',         registered: true },
  { code: 'CONTRATTO',          i18nKey: 'documenti.context_builders.CONTRATTO',          registered: true },
  { code: 'OFFERTA_COMMERCIALE', i18nKey: 'documenti.context_builders.OFFERTA_COMMERCIALE', registered: true },
  { code: 'ORDINE_VENDITA',     i18nKey: 'documenti.context_builders.ORDINE_VENDITA',     registered: true },
]

// Scopo: Helper per il dropdown PrimeVue Select. Ritorna un array di
//        opzioni con `code` (value) e `label` da risolvere via i18n nel
//        componente: `options.value = optionsForSelect(t)`.
export function contextBuilderOptions(t) {
  return CONTEXT_BUILDER_CODES.map(({ code, i18nKey, registered }) => ({
    code,
    label: t(i18nKey),
    registered,
  }))
}
