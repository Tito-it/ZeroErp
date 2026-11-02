// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia admin per `documenti.template_documenti`
//        (Tranche L). Pattern factory `createCrudStore` (startsEmpty:false,
//        lista parte piena). Lo store gestisce solo la testata template; il
//        ciclo vita delle versioni vive in `templateVersioni.js` per coerenza
//        con le API multi-livello del backend.
//
//        `userScoped: true` di default sul factory (memoria
//        feedback_pinia_userscoped: dati admin scoped per emittente
//        operatore -> reset al logout obbligatorio).
// ------------------------------------------------------------

import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'
import {
  createTemplateDocumento,
  getTemplateDocumento,
  listTemplateDocumenti,
  personalizzaTemplateDocumento,
  updateTemplateDocumento,
} from '../api/templateDocumenti'

export const useTemplateDocumentiStore = createCrudStore('config-template-documenti', {
  api: {
    list: listTemplateDocumenti,
    detail: getTemplateDocumento,
    create: createTemplateDocumento,
    update: updateTemplateDocumento,
  },
  tabEntity: TAB_ENTITIES.TEMPLATE_DOCUMENTI,
  // «Personalizza» (id dello standard, payload): la copia per un'azienda. Nello
  // stesso giro di scrittura di create/update: le altre tab ricaricano.
  extraActions: { personalizza: personalizzaTemplateDocumento },
  orderBy: 'codice',
  orderDir: 'asc',
  startsEmpty: false,
  filterDefaults: {
    attivo: true,
    tipo_documento_output_id: null,
    sorgente_tipo_id: null,
    emittente_fiscale_id: null,
    // «Standard»: solo i modelli di sistema (true) o solo quelli delle
    // aziende (false); null = tutti.
    standard: null,
  },
})
