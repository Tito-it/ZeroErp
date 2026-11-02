// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// ------------------------------------------------------------
// Scopo: client dell'anteprima IVA di riga.
//   POST /api/v1/vendite/iva/resolve/
//
// ⭐ Si mandano le COORDINATE del documento e l'articolo, e basta. Emittente,
//    billing account, utility e data li deriva il backend dalla testata — la
//    stessa che leggera' al salvataggio, cosi' cio' che si vede e cio' che
//    viene scritto vengono dalla stessa fonte.
// ⛔ Non esiste un parametro `imponibile`, ed e' voluto: con l'importo il
//    risolutore puo' rispondere con DUE parti (plafond che finisce a meta'
//    riga), e sui documenti quella spezzatura non si fa.

import api from '../../core/api'

export function resolveIvaRiga({ articoloId, documentoTipo, documentoId }) {
  return api.post('/vendite/iva/resolve/', {
    articolo_id: articoloId,
    documento_tipo: documentoTipo,
    documento_id: documentoId,
  })
}
