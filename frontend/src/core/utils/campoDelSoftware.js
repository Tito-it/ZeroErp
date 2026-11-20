// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: su una riga nata dal seed di primo impianto, il campo lo stabilisce
//        il programma? (regola del 2, ok Tid 2026-11-20 —
//        brief-db-seed-primo-impianto-non-si-riscrive §16.16).
// Note: ⭐ Trasporta, non deduce: l'elenco e' `campi_del_software` del
//       dettaglio, che il DB calcola con le stesse funzioni del guard che
//       rifiuta (`E_SEED_COLONNA_DEL_SOFTWARE`). Qui nessun elenco di colonne.
//       Una riga senza l'elenco (creazione, dettaglio non caricato, riga
//       dell'installazione: lista vuota) non ferma niente.
//       Fa da predicato a `senzaCampiFermi` per il PATCH.
// ------------------------------------------------------------

export function campoDelSoftware(riga, campo) {
  const campi = riga?.campi_del_software
  return Array.isArray(campi) && campi.includes(campo)
}
