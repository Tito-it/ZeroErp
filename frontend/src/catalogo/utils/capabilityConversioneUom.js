// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: CHE COSA SI PUO' FARE SU UNA CONVERSIONE VERSIONATA, letto dalla riga
//        che il backend consegna (2026-11-11, regola del 2, ok Tid — BE21-b/e
//        di brief-db-revisione-catalogo). Vale per la mappatura di un
//        articolo (`ArticoloUomForm`, `ArticoloUomDrawer`) e per la
//        conversione generale (`ConversioneUomDrawer`): le due viste di
//        dettaglio del DB pubblicano la stessa capability, dal BB
//        `catalogo.fn_uom_conversione_capability`, la regola con cui il guard
//        della storia rifiuta.
//        `capabilityConversioneUom(riga)` → { attivoFermo, motivoAttivo,
//        fineFerma, motivoFine, primaFine }; `chiaveMotivoUom(motivo)` → la
//        chiave i18n del motivo (`catalogo.motivo_<motivo>`);
//        `fraseMotivoUom(t, te, motivo)` → la frase a video;
//        `fermoDallaCapability(cap, campo)` → il campo che la capability
//        spegne, da togliere dal PATCH (con `senzaCampiFermi`).
//        ⭐ Le ultime due dal 2026-11-11 (regola del 2, ok Tid): erano
//        ricopiate identiche in `ArticoloUomForm` e `ConversioneUomDrawer`.
// Note: ⛔ Il FE TRASPORTA, non deduce: nessuna regola sulle date qui.
//       ⭐ Spegnere ed eliminare sono la STESSA regola nel DB («una conversione
//       con giorni passati non si spegne e non si cancella: si chiude»), quindi
//       il motivo dell'interruttore e' `motivo_non_eliminabile`; sulla riga
//       base e' `UOM_BASE_NON_ELIMINABILE`, che la frase dice per tutti e due.
//       ⚠️ Fail-closed: una riga che non porta la capability (`!== true`)
//       non si spegne e non si chiude. In creazione (`riga` null) tutto e'
//       libero: la regola e' sui giorni gia' passati, e una riga nuova non
//       ne ha.
// ------------------------------------------------------------
import { parseIsoDate } from '../../core/utils/date'
import { labelOrCode } from '../../core/utils/i18nLabel'

// Scopo: la chiave i18n di un motivo della vista (`UOM_STORIA_IN_VIGORE` →
//        `catalogo.motivo_uom_storia_in_vigore`); `null` senza motivo. Il
//        chiamante la rende con `labelOrCode` (chiave mancante ⇒ il codice).
export function chiaveMotivoUom(motivo) {
  return motivo ? `catalogo.motivo_${String(motivo).toLowerCase()}` : null
}

// Scopo: le tre risposte della capability per il form di una riga scritta.
export function capabilityConversioneUom(riga) {
  if (riga == null) {
    return { attivoFermo: false, motivoAttivo: null, fineFerma: false, motivoFine: null, primaFine: null }
  }
  const attivoFermo = riga.puo_cambiare_attivo !== true
  const fineFerma = riga.puo_chiudersi !== true
  return {
    attivoFermo,
    motivoAttivo: attivoFermo ? (riga.motivo_non_eliminabile ?? null) : null,
    fineFerma,
    motivoFine: fineFerma ? (riga.motivo_non_chiudibile ?? null) : null,
    // La prima fine ammessa (la piu' tarda fra l'inizio e ieri): la fine non
    // cambia i giorni gia' passati. Il DatePicker la usa come `min-date`.
    primaFine: parseIsoDate(riga.data_min_chiusura),
  }
}

// Scopo: la frase del motivo di un campo spento, '' senza motivo. Chiave i18n
//        mancante ⇒ il codice del motivo (fail-visible, `labelOrCode`).
//        `t`/`te` dal `useI18n()` del chiamante, per restare reattivi alla lingua.
export function fraseMotivoUom(t, te, motivo) {
  const chiave = chiaveMotivoUom(motivo)
  return chiave ? labelOrCode(t, te, chiave, motivo) : ''
}

// Scopo: il campo che la capability spegne (`attivo`, `valido_al`): fermo nel
//        PATCH, come quelli del lock. Gli altri campi non li giudica.
export function fermoDallaCapability(cap, campo) {
  if (campo === 'attivo') return cap.attivoFermo
  if (campo === 'valido_al') return cap.fineFerma
  return false
}
