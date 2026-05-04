// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia admin per `documenti.template_asset` (Tranche L).
//        Pattern factory `createCrudAdminStore` esteso con upload
//        multipart (factory non lo prevede: lo aggiungiamo come azione
//        custom riusando il factory + `defineStore` extension via
//        composizione).
//
//        L'API upload lavora con FormData (multipart): il flusso del
//        FE costruisce il FormData dal form drawer e chiama l'azione
//        dedicata. Tutto il resto (list/get/update) segue il factory.
//
//        `userScoped: true` di default (vedi factory).
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import {
  getTemplateAssetDocumento,
  listTemplateAssetDocumenti,
  updateTemplateAssetDocumento,
  uploadTemplateAssetDocumento,
} from '../api/templateAssetDocumenti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { ref } from 'vue'

const STORE_NAME = 'config-template-asset-documenti'
const EMIT_KEY = 'template_asset_documenti'

export const useTemplateAssetDocumentiStore = defineStore(STORE_NAME, () => {
  const { emitDataChanged } = useTabEvents()

  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  const filters = ref({
    search: '',
    attivo: true,
    asset_tipo_id: null,
    emittente_fiscale_id: null,
    limit: 25,
    offset: 0,
    order_by: 'codice',
    order_dir: 'asc',
  })

  // Scopo: Lista paginata. Min 3 caratteri per la search (coerente con
  //        `createCrudAdminStore`). Sotto soglia: clear silente.
  async function fetchList() {
    const f = filters.value
    const term = (f.search || '').trim()
    if (term.length > 0 && term.length < 3) {
      if (hasSearched.value) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
      }
      return
    }

    loading.value = true
    try {
      const params = { limit: f.limit, offset: f.offset }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (term.length >= 3) params.search = term
      if (f.attivo != null) params.attivo = f.attivo
      if (f.asset_tipo_id != null) params.asset_tipo_id = f.asset_tipo_id
      if (f.emittente_fiscale_id != null) params.emittente_fiscale_id = f.emittente_fiscale_id

      const res = await listTemplateAssetDocumenti(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    const res = await getTemplateAssetDocumento(id)
    return res.data.data
  }

  // Scopo: Upload asset (multipart). Il caller costruisce il FormData
  //        con `file` + i metadati. Lo store inoltra al BE e notifica
  //        i tab in ascolto via `emitDataChanged`.
  async function upload(formData) {
    const res = await uploadTemplateAssetDocumento(formData)
    emitDataChanged(EMIT_KEY, res.data.data.id)
    return res.data.data
  }

  // Scopo: PATCH metadati (no sostituzione file: per cambiare il file
  //        si carica un nuovo asset, Decisione 66).
  async function update(id, payload) {
    const res = await updateTemplateAssetDocumento(id, payload)
    emitDataChanged(EMIT_KEY, id)
    return res.data.data
  }

  return {
    items, totalRecords, loading, hasSearched, filters,
    fetchList, fetchDetail, upload, update,
  }
}, { userScoped: true })
