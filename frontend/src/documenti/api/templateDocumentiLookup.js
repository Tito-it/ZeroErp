// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API leggero per la lookup dei template applicabili
//        (Tranche M). Riusa l'endpoint generale Tranche C
//        `/documenti/templates/` con i filtri sorgente_tipo_id +
//        emittente_fiscale_id + attivo=true. Usato dal pulsante
//        "Genera PDF" per:
//         - decidere se aprire il dialog scelta (>1 template);
//         - popolare il dialog stesso.
// ------------------------------------------------------------

import api from '../../core/api'

// Scopo: Lista template applicabili per (sorgente_tipo, emittente).
//        Ritorna l'envelope paginato standard. Page size 200 e' un
//        cap pratico: in v1 i template per coppia sono pochi, ma
//        manteniamo il filtro per evitare risposte non paginate.
export function listTemplateApplicabili({ sorgenteTipoId, emittenteFiscaleId, tipoDocumentoOutputId = null }) {
  const params = {
    sorgente_tipo_id: sorgenteTipoId,
    emittente_fiscale_id: emittenteFiscaleId,
    attivo: true,
    page_size: 200,
  }
  if (tipoDocumentoOutputId != null) {
    params.tipo_documento_output_id = tipoDocumentoOutputId
  }
  return api.get('/documenti/templates/', { params })
}
