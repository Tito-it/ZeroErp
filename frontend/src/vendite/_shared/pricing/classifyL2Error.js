// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: Helper puro condiviso (regola del 2, refactor-prezzi 2026-06-01) per
//        classificare un errore axios come violazione L2 del pricing
//        (sconto/maggiorazione eccessivi). Usato da preventivi, contratti e
//        offerte: dove i tre drawer mostrano il banner inline + CTA "richiedi
//        approvazione" invece del toast standard.
//
//        Nessun side-effect: ritorna l'oggetto banner se il codice errore e'
//        nella whitelist L2, altrimenti `null` (il caller decide il fallback,
//        tipicamente `notify.error`). I codici L2 sono centralizzati in
//        `useLimitiPricing` (allineati a `pricing_service.L2_ERROR_CODES` BE).

import { extractApiError, extractApiErrorCode } from '../../../core/utils/apiError'

// Ritorna { code, message, detail } se l'errore axios porta un codice L2,
// altrimenti null. `l2ErrorCodes` arriva dal caller (da `useLimitiPricing`).
export function classifyL2Error(err, { fallbackMessage, l2ErrorCodes }) {
  const code = extractApiErrorCode(err)
  if (!l2ErrorCodes.includes(code)) return null
  return {
    code,
    message: extractApiError(err, fallbackMessage),
    detail: err?.response?.data?.error?.detail || '',
  }
}
