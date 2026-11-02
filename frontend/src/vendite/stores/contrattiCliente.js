// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista CONTRATTI DI UN CLIENTE (`vendite.contratti`
//        filtrata sul conto di fatturazione), consumata da
//        `ContrattiBillingAccountDrawer` attraverso `useDrawerTabLista`.
// Note: ⭐ E' UNO STORE SUO, non `useContrattiStore`: quello porta la lista
//       della schermata Contratti, col suo floor `data_da` a 60 giorni e i
//       filtri che l'operatore ci ha messo. Condividerlo farebbe sparire dal
//       drawer i contratti vecchi del cliente e scriverebbe i filtri di una
//       schermata nell'altra (`feedback_estrarre_non_condividere_stato`).
//       ⭐ Il cliente e' il PADRE (contesto), non un filtro: al cambio cliente
//       i filtri si azzerano, lui si riscrive. Il backend lo riceve come
//       `billing_account_id`, lo stesso filtro della lista contratti.
//       ⛔ Prima (fino al 2026-09-26) il drawer chiedeva `limit: 50` e
//       filtrava lo STATO sul client: un cliente con piu' di 50 contratti ne
//       perdeva qualcuno senza avviso, e il filtro guardava solo quei 50.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { listContratti } from '../api/contratti'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useContrattiClienteStore = storePerIstanza('vendite-contratti-cliente', (id) => createListaStore(id,
  {
    fetchPage: (billingAccountId, params) =>
      listContratti({ ...params, billing_account_id: billingAccountId }),
    parentField: 'billingAccountId',
    // Il cliente e' gia' scelto quando il drawer si apre.
    startsEmpty: false,
    filterDefaults: { stato_doc_contratto_id: null },
    // Il piu' recente in cima, come nella lista contratti.
    orderBy: 'valido_dal',
    orderDir: 'desc',
  },
))
