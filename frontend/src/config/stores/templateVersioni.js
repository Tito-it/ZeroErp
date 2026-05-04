// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia per il ciclo vita versioni di un singolo template
//        documentale (Tranche L). 5 azioni POST/PATCH/DELETE/clona/
//        pubblica + `fetchList` / `fetchDetail`. Differente dal CRUD
//        admin standard perche':
//         - le versioni vivono SOTTO un template parent (URL nidificato);
//         - non c'e' paginazione (ciclo BOZZA->PUBBLICATA->OBSOLETA per
//           design ha cardinalita' contenuta);
//         - 3 comandi di transizione di stato dedicati (clona, pubblica,
//           delete BOZZA).
//
//        `userScoped: true` per coerenza con le memorie del progetto:
//        i dati versione corrente del template aperto contengono html/
//        css/markdown — non devono leakare al cambio utente.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  clonaTemplateVersione,
  createTemplateVersione,
  deleteTemplateVersione,
  getTemplateVersione,
  listTemplateVersioni,
  pubblicaTemplateVersione,
  updateTemplateVersione,
} from '../api/templateDocumenti'
import { useTabEvents } from '../../core/composables/useTabEvents'

const STORE_NAME = 'config-template-versioni'
const EMIT_KEY = 'template_versioni'

export const useTemplateVersioniStore = defineStore(STORE_NAME, () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const loading = ref(false)
  const currentTemplateId = ref(null)

  // Scopo: Carica le versioni del template parent. Sostituisce i dati
  //        precedenti in modo idempotente: piu' chiamate consecutive su
  //        template diversi non fanno merge. La memoria
  //        feedback_componente_riusabile_watch suggerisce di richiamare
  //        questa fn quando cambia `template_id`.
  async function fetchList(templateId, params = {}) {
    if (!templateId) {
      items.value = []
      currentTemplateId.value = null
      return
    }
    loading.value = true
    try {
      const res = await listTemplateVersioni(templateId, params)
      // L'endpoint versioni NON usa paginated_envelope: ritorna
      // direttamente {results: [...]}.
      items.value = res.data.data.results || []
      currentTemplateId.value = templateId
    } finally {
      loading.value = false
    }
  }

  // Scopo: Dettaglio versione singola (incluso payload html/css/markdown).
  async function fetchDetail(templateId, versioneId) {
    const res = await getTemplateVersione(templateId, versioneId)
    return res.data.data
  }

  // Scopo: Crea nuova versione BOZZA.
  async function create(templateId, payload) {
    const res = await createTemplateVersione(templateId, payload)
    emitDataChanged(EMIT_KEY, res.data.data.id)
    return res.data.data
  }

  // Scopo: Update versione BOZZA. PUBBLICATA -> errore service-side
  //        (E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE) + trigger DB A1.
  async function update(templateId, versioneId, payload) {
    const res = await updateTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, versioneId)
    return res.data.data
  }

  // Scopo: Hard DELETE versione (solo BOZZA, trigger DB A2 block_delete).
  async function destroy(templateId, versioneId) {
    await deleteTemplateVersione(templateId, versioneId)
    emitDataChanged(EMIT_KEY, versioneId)
  }

  // Scopo: Clona versione esistente -> nuova BOZZA.
  async function clona(templateId, versioneId, payload = {}) {
    const res = await clonaTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, res.data.data.id)
    return res.data.data
  }

  // Scopo: Transizione BOZZA -> PUBBLICATA con `valido_dal` obbligatorio.
  async function pubblica(templateId, versioneId, payload) {
    const res = await pubblicaTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, versioneId)
    return res.data.data
  }

  return {
    items, loading, currentTemplateId,
    fetchList, fetchDetail, create, update, destroy, clona, pubblica,
  }
}, { userScoped: true })
