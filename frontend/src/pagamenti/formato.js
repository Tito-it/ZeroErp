// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La formattazione degli importi negli slot custom di questo dominio.
// Note: ⚠️ Serve SOLO dove il rendering della cella e' nostro: le colonne
//       dichiarate `currency_eur` a catalogo le formatta gia'
//       `CellaConfigurabile`, e rifarlo sarebbe una seconda sede.
//       ⭐ `placeholder: '—'` e non stringa vuota, ed e' il punto: qui `null`
//       significa «il conto non si applica» (un importo mai dichiarato, un
//       saldo che non esiste) — una cella VUOTA si legge come un dato perso,
//       il trattino come una risposta.
//       📮 Il ripiego a trattino e' una convenzione di tutto il progetto, oggi
//       scritta a mano in decine di template (`{{ x || '—' }}`). Se altri
//       domini adotteranno questa forma, `formatCurrency` in `core/utils/format`
//       e' la sede naturale di un `placeholder` di default: dichiarato, non
//       fatto di mia iniziativa.
// ------------------------------------------------------------

import { formatCurrency } from '../core/utils/format'

// Scopo: importo in euro, col trattino quando il valore non c'e'.
export function euro(v) {
  return formatCurrency(v, { placeholder: '—' })
}
