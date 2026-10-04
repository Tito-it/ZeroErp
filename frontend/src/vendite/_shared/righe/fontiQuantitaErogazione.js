// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// ------------------------------------------------------------
// Scopo: la matrice tipo di erogazione × fonte della quantita' attesa di una
//   riga commerciale (riga di contratto, eccezione di offerta): quali fonti
//   una tendina offre per un'erogazione, con quale scelta predefinita e con
//   quale segnale di uso atipico.
//
// ⭐ E' lo specchio di UNA regola del DB, uguale sulle due tabelle: i CHECK
//    `chk_contrighe_coerenza_fonte_erogazione` e
//    `chk_offerte_eccezioni_coerenza_fonte_erogazione` vietano le stesse
//    combinazioni, e `fn_push_offerta_a_contratto` ricopia la coppia
//    dall'offerta al contratto. Il default e' quello del trigger
//    `script.trgfn_righe_default_fonte_qta`. Qui si FILTRA la tendina; il
//    giudice resta il DB.
//
// Estratto il 2026-10-04 (regola del 2, ok Tid): erano due copie in
// `ContrattoRigheDrawer` e `OffertaEccezioniDrawer`, gia' divergenti — la
// copia dell'offerta non aveva ORARIO (una riga ORARIO letta dal DB mostrava
// la tendina della fonte vuota) ne' i segnali di uso atipico.
//
// `severity: 'warn'` = combinazione ammessa ma atipica (🟡 nella matrice);
// `default: true` = la scelta proposta quando l'erogazione cambia.
// TIMESHEET resta fuori finche' il modulo rendicontazione ore non esiste
// (il CHECK lo ammette con ORARIO).
// Riferimento: docs/it/dev/work-done/refactor-contratti-fonte-quantita.md §3.

import { FONTE_QUANTITA_ATTESA, TIPO_EROGAZIONE } from '../../constants'

export const FONTI_PER_TIPO_EROGAZIONE = Object.freeze({
  [TIPO_EROGAZIONE.CANONE]: Object.freeze([
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ]),
  [TIPO_EROGAZIONE.UNA_TANTUM]: Object.freeze([
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ]),
  [TIPO_EROGAZIONE.ORARIO]: Object.freeze([
    { value: FONTE_QUANTITA_ATTESA.FISSA, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, default: true },
    // { value: FONTE_QUANTITA_ATTESA.TIMESHEET },  // attivare quando il modulo timesheet esistera'
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI, severity: 'warn' },
  ]),
  [TIPO_EROGAZIONE.CONSUMO]: Object.freeze([
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.LETTURE, default: true },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ]),
})

// Scopo: le fonti ammesse per un'erogazione; nessuna per un'erogazione
//        assente o sconosciuta (che fare senza erogazione lo decide il form).
export function fontiPerErogazione(tipo) {
  return FONTI_PER_TIPO_EROGAZIONE[tipo] || []
}

// Scopo: la fonte proposta per un'erogazione, o null.
export function fonteDefaultPerErogazione(tipo) {
  return fontiPerErogazione(tipo).find((f) => f.default)?.value ?? null
}
