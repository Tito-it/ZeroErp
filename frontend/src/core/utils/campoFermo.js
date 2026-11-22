// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IN MODIFICA, IL CAMPO DI QUESTA RIGA E' FERMO? (regola del 2, ok Tid
//        2026-11-22 — `/verifica` di brief-db-revisione-ui, BE12). Fermo vuol
//        dire: il DB rifiuterebbe di cambiarlo, quindi il form lo spegne e il
//        PATCH non lo porta (`senzaCampiFermi`).
// Note: ⭐ Trasporta, non deduce: due elenchi della RIGA, entrambi calcolati
//       dal DB con le stesse regole di chi rifiuta:
//         - `campi_del_software`, il programma lo stabilisce su una riga nata
//           dal seed (`campoDelSoftware`, `E_SEED_COLONNA_DEL_SOFTWARE`);
//         - `non_editable_fields`, fermo per modello: i lucchetti di colonna
//           e i lock condizionali (`dbops.fn_non_editable_fields`, per
//           esempio `E_UI_COLONNA_CODICE_IMMUTABILE`).
//       Qui nessun nome di campo: prima i drawer di `ui` scrivevano
//       `campo === 'codice'`, una copia del lucchetto del DB.
//       ⚠️ Il predicato non sa se si sta creando: in creazione la riga non
//       c'e' e niente e' fermo, e il componente lo dice da se'
//       (`isEdit && campoFermo(riga, campo)`), come per `campoDelSoftware`.
//       ⚠️ Il motivo a video resta di `campoDelSoftware` (`MotivoDelProgramma`):
//       un campo fermo per modello non e' «del programma».
// ------------------------------------------------------------

import { campoDelSoftware } from './campoDelSoftware'

export function campoFermo(riga, campo) {
  if (campoDelSoftware(riga, campo)) return true
  const fermi = riga?.non_editable_fields
  return Array.isArray(fermi) && fermi.includes(campo)
}
