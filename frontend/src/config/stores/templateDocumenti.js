// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia admin per `documenti.template_documenti`
//        (Tranche L). Pattern factory `createCrudAdminStore`. Lo
//        store gestisce solo la testata template; il ciclo vita
//        delle versioni vive in `templateVersioni.js` per coerenza
//        con le API multi-livello del backend.
//
//        `userScoped: true` di default sul factory (memoria
//        feedback_pinia_userscoped: dati admin scoped per emittente
//        operatore -> reset al logout obbligatorio).
// ------------------------------------------------------------

import { createCrudAdminStore } from '../../core/composables/createCrudAdminStore'
import {
  createTemplateDocumento,
  getTemplateDocumento,
  listTemplateDocumenti,
  updateTemplateDocumento,
} from '../api/templateDocumenti'

export const useTemplateDocumentiStore = createCrudAdminStore({
  storeName: 'config-template-documenti',
  api: {
    list: listTemplateDocumenti,
    get: getTemplateDocumento,
    create: createTemplateDocumento,
    update: updateTemplateDocumento,
  },
  defaultOrderBy: 'codice',
  defaultOrderDir: 'asc',
  emitKey: 'template_documenti',
  // Filtri specifici lato BE (mappati da nome client a nome param server).
  extraFilters: {
    tipo_documento_output_id: 'tipo_documento_output_id',
    sorgente_tipo_id: 'sorgente_tipo_id',
    emittente_fiscale_id: 'emittente_fiscale_id',
  },
})
