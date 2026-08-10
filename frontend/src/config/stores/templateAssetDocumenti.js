// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia admin per `documenti.template_asset` (Tranche L).
//        Store hand-rolled (NON usa la factory `createCrudStore`) perche'
//        estende il pattern CRUD admin con upload multipart e azioni custom.
//        Mantiene lo stesso comportamento "lista parte piena" + gate search
//        min-3-char.
//
//        L'API upload lavora con FormData (multipart): il flusso del
//        FE costruisce il FormData dal form drawer e chiama l'azione
//        dedicata. Tutto il resto (list/get/update) segue il factory.
//
//        `userScoped: true` di default (vedi factory).
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import {
  downloadTemplateAssetDocumento,
  getTemplateAssetDocumento,
  listTemplateAssetDocumenti,
  updateTemplateAssetDocumento,
  uploadTemplateAssetDocumento,
} from '../api/templateAssetDocumenti'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { ref } from 'vue'

const STORE_NAME = 'config-template-asset-documenti'
const EMIT_KEY = 'template_asset_documenti'

export const useTemplateAssetDocumentiStore = defineStore(STORE_NAME, () => {
  const { emitDataChanged } = useTabEvents()


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

  // Lista via BB condiviso (migrazione 2026-08-10): porta la guardia di versione
  // anti-race che qui mancava. `ricercaCorta: 'svuota'` conserva ESATTAMENTE l'UX
  // di prima — parte piena, ma una ricerca sotto i 3 caratteri svuota invece di
  // lasciare a video righe che non c'entrano con quello che si sta scrivendo.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    ricercaCorta: 'svuota',
    buildParams: (f, searchTerm) => {
      const params = { limit: f.limit, offset: f.offset }
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      if (searchTerm.length >= 3) params.search = searchTerm
      if (f.attivo != null) params.attivo = f.attivo
      if (f.asset_tipo_id != null) params.asset_tipo_id = f.asset_tipo_id
      if (f.emittente_fiscale_id != null) params.emittente_fiscale_id = f.emittente_fiscale_id
      return params
    },
    fetchPage: listTemplateAssetDocumenti,
  })

  async function fetchDetail(id) {
    const res = await getTemplateAssetDocumento(id)
    return res.data.data
  }

  async function download(id) {
    const res = await downloadTemplateAssetDocumento(id)
    return {
      blob: res.data,
      fileName: extractFileName(res) || `asset-${id}`,
    }
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
    fetchList, fetchDetail, download, upload, update,
  }
}, { userScoped: true })

function extractFileName(response) {
  const disposition = response?.headers?.['content-disposition']
  if (!disposition) return null
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1])
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || null
}
