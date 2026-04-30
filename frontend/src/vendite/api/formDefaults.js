// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: API client per gli endpoint form-defaults vendite (Fase 2.B3-B5
//        refactor frontend vendite). Tutti GET, area `vendite` LETTURA.
//        Single source of truth lato BE: BillingAccountRepository +
//        ListiniRepository + ParameterService combinati.
import api from '../../core/api'

// Scopo: Defaults form contratto. Se billingAccountId presente, popola
//        categoria_cliente_id_snapshot/utility/istanza dal BA. Sempre presente
//        default_data e default_valido_dal (parameters lead_gg).
export function getContrattoFormDefaults(billingAccountId = null) {
  const params = billingAccountId ? { billing_account_id: billingAccountId } : {}
  return api.get('/vendite/contratti/form-defaults/', { params })
}

// Scopo: Defaults form preventivo. Se billingAccountId presente, popola
//        valuta_id/termine_pagamento_id/iva_id/modalita_pagamento_id dal
//        cliente del BA + utility/istanza dal BA. Sempre default_validita_al
//        da parameter VALIDITA_GG.
export function getPreventivoFormDefaults(billingAccountId = null) {
  const params = billingAccountId ? { billing_account_id: billingAccountId } : {}
  return api.get('/vendite/preventivi/form-defaults/', { params })
}

// Scopo: Defaults nuova versione listino: default_valido_dal (oggi+lead_gg)
//        + lista BOZZE esistenti (warning UX).
export function getVersioneNewDefaults(listinoId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/form-defaults/`)
}

// Scopo: Defaults clone versione: codice = source + suffisso, valido_dal =
//        oggi + lead_gg, min_valido_dal = source.valido_dal, is_retroactive_default.
export function getVersioneCloneDefaults(listinoId, srcVersioneId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/${srcVersioneId}/clone-defaults/`)
}

// Scopo: Defaults chiusura versione: default_valido_al (existing oppure
//        oggi+lead_gg), current_valido_al (per UX "ha gia chiusura").
export function getVersioneCloseDefaults(listinoId, versioneId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/${versioneId}/close-defaults/`)
}
