// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL CLIENTE (E LA FORNITURA) DI UN FORM, RICOSTRUITI PER IL LOOKUP
//        quando il drawer apre un documento esistente. Il form ha l'id; il
//        lookup vuole l'oggetto ricco (`<campo>_obj`: ragione sociale, codice,
//        id fiscale, utility, PDP) per l'etichetta. Si rilegge dal server, con
//        la stessa forma che il lookup riceve quando l'operatore sceglie.
// Note: ⭐ Regola del 2 (2026-10-19, ok Tid). Fino ad allora i drawer di
//       vendita lo facevano in due modi: preventivo, DDT e ordine con la
//       stessa `try/catch` ricopiata (quattro copie); offerta e contratto
//       costruendo l'oggetto a mano dai campi del dettaglio, con la chiave
//       sbagliata della ragione sociale (`ragione_sociale` invece di
//       `ragione_sociale_completa`): riaperto il documento, il campo mostrava
//       il solo codice (collaudo di Tid).
//       ⚠️ Best-effort: se la lettura fallisce il campo resta col solo id e
//       l'operatore puo' ri-cercare. ⚠️ Si scrive SOLO se il form punta ancora
//       allo stesso id: una risposta lenta non sovrascrive un cliente scelto
//       nel frattempo. Il `_obj` e' fuori dal confronto «modificato»
//       (`useDrawerFormPreserve` ignora `_obj`): scriverlo dopo `fissa()` non
//       sporca il form.
// ------------------------------------------------------------

import { getBillingAccountLookupById, getIstanzaUtilityLookupById } from '../apiCore'

// Scopo: legge l'oggetto del lookup e lo mette in `form[campoObj]` se il form
//        ha ancora `form[campoId] === id`.
async function ripristina(form, id, { campoId, campoObj, leggi }) {
  if (id == null) return
  try {
    const res = await leggi(id)
    const obj = res?.data?.data
    if (obj && form[campoId] === id) form[campoObj] = obj
  } catch {
    // Best-effort: il campo resta col solo id, l'operatore puo' ri-cercare.
  }
}

// Scopo: il billing account del form (`billing_account_id` → `billing_account_obj`).
export function ripristinaBillingAccount(form, id) {
  return ripristina(form, id, {
    campoId: 'billing_account_id',
    campoObj: 'billing_account_obj',
    leggi: getBillingAccountLookupById,
  })
}

// Scopo: l'istanza del form (`istanza_utility_id` → `istanza_utility_obj`).
export function ripristinaIstanzaUtility(form, id) {
  return ripristina(form, id, {
    campoId: 'istanza_utility_id',
    campoObj: 'istanza_utility_obj',
    leggi: getIstanzaUtilityLookupById,
  })
}
