// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la lettura «come si puo' erogare un articolo su una riga del
//        documento» (`GET …/<id>/righe/erogazioni/?articolo_id=<uuid>`), per i
//        documenti con listino ed eccezioni: contratto e offerta. Regola del 2:
//        un endpoint per dominio sulla stessa base BE (`RigaErogazioniView`).
// Note: brief-db-offerta-emissione-ed-erogazione B-R4, 2026-10-07. Le righe
//       le mette in forma `erogazioniRiga.js`; il consumer e'
//       `RigheEccezioniDrawer` (prop `erogazioniArticolo`).
//       ⚠️ Non sta in `makeRigheListaApi`: quella la usano tutti i documenti di
//       vendita, l'endpoint esiste solo per i due con eccezioni.
// ------------------------------------------------------------
import api from '../../../core/api'

// Scopo: la chiamata per un dominio (`/vendite/contratti`, `/vendite/offerte`).
export function makeRigaErogazioniApi(base) {
  return {
    // (documentoId, articoloId) → envelope dei lookup `data.results`: le
    // combinazioni (erogazione, fonte) ammesse, il default in testa.
    listRigaErogazioni: (documentoId, articoloId) =>
      api.get(`${base}/${documentoId}/righe/erogazioni/`, {
        params: { articolo_id: articoloId },
      }),
  }
}
