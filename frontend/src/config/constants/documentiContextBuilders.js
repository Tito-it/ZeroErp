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
//        v1: solo PREVENTIVO e' registrato lato BE (Tranche J).
//        CONTRATTO/ORDINE sono placeholder per coerenza UX (la
//        creazione template con builder non registrato sara' rifiutata
//        dal BE alla generazione documento, Decisione 18+74).
// ------------------------------------------------------------

export const CONTEXT_BUILDER_CODES = [
  { code: 'PREVENTIVO', i18nKey: 'documenti.context_builders.PREVENTIVO', registered: true },
  { code: 'CONTRATTO',  i18nKey: 'documenti.context_builders.CONTRATTO',  registered: false },
  { code: 'ORDINE',     i18nKey: 'documenti.context_builders.ORDINE',     registered: false },
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
