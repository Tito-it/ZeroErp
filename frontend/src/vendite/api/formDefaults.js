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

// Scopo: Defaults form ordine di vendita. Senza BA ritorna valuta_id dalla
//        catena EF utente → gestore (BB resolve_valuta_default); con BA aggiunge
//        utility BA-derived. La utility di default globale (DEFAULT_UTILITY) la
//        risolve il FE via useUtilityDefaultId, come negli altri drawer.
export function getOrdineFormDefaults(billingAccountId = null) {
  const params = billingAccountId ? { billing_account_id: billingAccountId } : {}
  return api.get('/vendite/ordini/form-defaults/', { params })
}

// Scopo: Defaults form DDT di vendita. Senza BA ritorna valuta_id dalla catena
//        EF utente → gestore (BB resolve_valuta_default); con BA aggiunge utility
//        BA-derived + valuta del cliente. Il DDT è un documento di trasporto:
//        niente termini/modalita di pagamento in testata. La utility di default
//        globale (DEFAULT_UTILITY) la risolve il FE via useUtilityDefaultId, come
//        negli altri drawer. L'emittente NON è qui: lo risolve il trigger DB
//        (memorizzato sulla testata) e il FE lo mostra read-only dal detail.
export function getDdtFormDefaults(billingAccountId = null) {
  const params = billingAccountId ? { billing_account_id: billingAccountId } : {}
  return api.get('/vendite/ddt/form-defaults/', { params })
}

// Scopo: Defaults form offerta commerciale. Se billingAccountId presente,
//        popola categoria_cliente_id_snapshot + utility/istanza + valuta_id
//        dal BA. Senza BA, la valuta arriva comunque dalla catena
//        EF utente → gestore (BB resolve_valuta_default).
export function getOffertaFormDefaults(billingAccountId = null) {
  const params = billingAccountId ? { billing_account_id: billingAccountId } : {}
  return api.get('/vendite/offerte/form-defaults/', { params })
}

// Scopo: Defaults nuova versione listino: default_valido_dal (oggi+lead_gg)
//        + lista BOZZE esistenti (warning UX).
export function getVersioneNewDefaults(listinoId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/form-defaults/`)
}

// Scopo: Defaults clone versione: codice = source + suffisso, valido_dal =
//        oggi + lead_gg, is_retroactive_default. D2 (la copia non comincia
//        prima della sorgente) la dice il verbo del DB, sul campo valido_dal.
export function getVersioneCloneDefaults(listinoId, srcVersioneId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/${srcVersioneId}/clone-defaults/`)
}

// Scopo: Defaults chiusura versione: default_valido_al (existing oppure
//        oggi+lead_gg), current_valido_al (per UX "ha gia chiusura").
export function getVersioneCloseDefaults(listinoId, versioneId) {
  return api.get(`/vendite/listini/${listinoId}/versioni/${versioneId}/close-defaults/`)
}
